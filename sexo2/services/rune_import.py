"""Import of a chosen rune page into the client, one managed page only.

State per champion-select session (champ select identity + champion):

- ``displayed``: recommendations shown to the player. Showing never imports.
- ``chosen``: the page the player picked (card click) or edited.
- ``applied``: the last page whose import the client confirmed by reading the
  page back (styles, perks, and that it is the current page).

A pick imports at once. Edits are validated, debounced and coalesced: at most
one import runs at a time, and when it ends the newest chosen page, if any,
follows. A new session, a new champion or leaving champion select bumps the
epoch: queued work stops before its next write and late answers are dropped.

Only the managed page (name starting with ``MANAGED_PAGE_PREFIX``) is ever
written. Without one and without a free slot the import fails with
``no_free_page``; personal pages are never edited or deleted.

LCU calls block, so they run on an injected executor (one serial worker in
production, a manual queue in tests); the debounce uses an injected scheduler.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Protocol

from lcu.features.lcu_perks import PageBody, PerksError, RunePage
from sexo2.services.rune_rules import PageSpec, StyleCatalog, Violation, validate_page
from sexo2.services.work_queue import SerialWorker

log = logging.getLogger(__name__)

# Provisional name, pending approval (docs/produto/decisoes.md, D-113).
MANAGED_PAGE_PREFIX = "SEXO2"
MANAGED_PAGE_NAME = MANAGED_PAGE_PREFIX
EDIT_DEBOUNCE_S = 0.3


@dataclass(frozen=True)
class SessionKey:
    """Identity of one champion-select session for one champion."""

    champ_select: str
    champion_id: int


class Cancellable(Protocol):
    def cancel(self) -> None: ...


class Scheduler(Protocol):
    def call_later(self, delay: float, callback: Callable[[], None]) -> Cancellable: ...


class Executor(Protocol):
    def submit(self, work: Callable[[], None]) -> bool: ...


class PerksClient(Protocol):
    def pages(self) -> list[RunePage]: ...

    def current_page(self) -> RunePage: ...

    def owned_page_count(self) -> int: ...

    def create_page(self, body: PageBody) -> RunePage: ...

    def update_page(self, page_id: int, body: PageBody) -> None: ...

    def set_current(self, page_id: int) -> None: ...


class TimerScheduler:
    """One short-lived timer per debounce window; nothing runs while idle."""

    def call_later(self, delay: float, callback: Callable[[], None]) -> Cancellable:
        timer = threading.Timer(delay, callback)
        timer.daemon = True
        timer.start()
        return timer


class SerialExecutor:
    """Runs imports one at a time on the shared serial worker pattern."""

    def __init__(self, name: str = "SEXO2-Rune-import") -> None:
        self._worker = SerialWorker(name)

    def submit(self, work: Callable[[], None]) -> bool:
        return self._worker.submit(work, lambda error: log.error("[RUNES] import failed: %s", type(error).__name__))

    def close(self) -> bool:
        return self._worker.close()


@dataclass(frozen=True)
class RuneImportSnapshot:
    session: SessionKey | None
    displayed: tuple[PageSpec, ...]
    chosen: PageSpec | None
    applied: PageSpec | None
    pending: bool
    error: str | None
    violations: tuple[Violation, ...] = ()


class _Abort(Exception):
    """An import stopped before confirmation; ``code`` says why."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RuneImportController:
    def __init__(
        self,
        perks: PerksClient,
        *,
        can_edit: Callable[[], bool],
        executor: Executor | None = None,
        scheduler: Scheduler | None = None,
        debounce: float = EDIT_DEBOUNCE_S,
        on_change: Callable[[RuneImportSnapshot], None] | None = None,
    ) -> None:
        self._perks = perks
        self._can_edit = can_edit
        self._executor = executor if executor is not None else SerialExecutor()
        self._scheduler = scheduler if scheduler is not None else TimerScheduler()
        self._debounce = debounce
        self._on_change = on_change
        self._lock = threading.RLock()
        self._catalog: StyleCatalog | None = None
        self._session: SessionKey | None = None
        self._epoch = 0
        self._generation = 0
        self._displayed: tuple[PageSpec, ...] = ()
        self._chosen: PageSpec | None = None
        self._chosen_generation = 0
        self._applied: PageSpec | None = None
        self._applied_generation = 0
        self._in_flight: int | None = None
        self._timer: Cancellable | None = None
        self._timer_token: object | None = None
        self._error: str | None = None
        self._violations: tuple[Violation, ...] = ()

    # Public API -----------------------------------------------------------

    def set_catalog(self, catalog: StyleCatalog | None) -> None:
        with self._lock:
            self._catalog = catalog

    def set_session(self, session: SessionKey | None) -> RuneImportSnapshot:
        """Enter a session/champion, or ``None`` when leaving champion select."""
        with self._lock:
            if session != self._session:
                self._epoch += 1
                self._cancel_timer()
                self._session = session
                self._displayed = ()
                self._chosen = None
                self._applied = None
                self._applied_generation = self._generation
                self._in_flight = None
                self._error = None
                self._violations = ()
            snapshot = self._snapshot()
        return self._notify(snapshot)

    def display(self, pages: list[PageSpec]) -> RuneImportSnapshot:
        with self._lock:
            if self._session is not None:
                self._displayed = tuple(pages)
            snapshot = self._snapshot()
        return self._notify(snapshot)

    def choose(self, page: PageSpec) -> RuneImportSnapshot:
        """The player picked a page: validate and import immediately."""
        with self._lock:
            if self._accept(page):
                self._send()
            snapshot = self._snapshot()
        return self._notify(snapshot)

    def edit(self, page: PageSpec) -> RuneImportSnapshot:
        """The player changed the page: valid edits are sent after a pause."""
        with self._lock:
            if self._accept(page):
                self._cancel_timer()
                token = object()
                self._timer_token = token
                self._timer = self._scheduler.call_later(self._debounce, lambda: self._on_timer(token))
            snapshot = self._snapshot()
        return self._notify(snapshot)

    def confirm(self) -> RuneImportSnapshot:
        """Send the chosen page now instead of waiting for the debounce."""
        with self._lock:
            if self._chosen is not None and self._chosen_generation > self._applied_generation:
                self._send()
            snapshot = self._snapshot()
        return self._notify(snapshot)

    def back(self) -> RuneImportSnapshot:
        """Leave the editor: drop unsent edits and keep the confirmed page."""
        with self._lock:
            self._cancel_timer()
            self._chosen = None
            self._violations = ()
            snapshot = self._snapshot()
        return self._notify(snapshot)

    def snapshot(self) -> RuneImportSnapshot:
        with self._lock:
            return self._snapshot()

    # State changes (lock held) ---------------------------------------------

    def _snapshot(self) -> RuneImportSnapshot:
        return RuneImportSnapshot(
            session=self._session,
            displayed=self._displayed,
            chosen=self._chosen,
            applied=self._applied,
            pending=self._timer is not None or self._in_flight is not None,
            error=self._error,
            violations=self._violations,
        )

    def _accept(self, page: PageSpec) -> bool:
        if self._session is None:
            self._error = "no_session"
            return False
        if self._catalog is None:
            self._error = "catalog_unavailable"
            return False
        violations = validate_page(page, self._catalog)
        if violations:
            self._error = "invalid_page"
            self._violations = tuple(violations)
            return False
        self._generation += 1
        self._chosen = page
        self._chosen_generation = self._generation
        self._error = None
        self._violations = ()
        return True

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = None
        self._timer_token = None

    def _on_timer(self, token: object) -> None:
        with self._lock:
            if token is not self._timer_token:
                return
            self._timer = None
            self._timer_token = None
            self._send()
            snapshot = self._snapshot()
        self._notify(snapshot)

    def _send(self) -> None:
        self._cancel_timer()
        if self._chosen is None or self._session is None or self._in_flight is not None:
            return  # A running import sends the newest choice when it ends.
        epoch, generation, page = self._epoch, self._chosen_generation, self._chosen
        self._in_flight = generation
        if not self._executor.submit(lambda: self._run(epoch, generation, page)):
            self._in_flight = None
            self._error = "busy"

    # Worker ------------------------------------------------------------------

    def _run(self, epoch: int, generation: int, page: PageSpec) -> None:
        try:
            self._import(epoch, page)
            outcome = None
        except _Abort as aborted:
            outcome = aborted.code
        except PerksError as error:
            log.warning("[RUNES] import failed: %s", error)
            outcome = f"lcu_{error.code}"
        except Exception:
            log.exception("[RUNES] unexpected import failure")
            outcome = "unexpected"
        self._finish(epoch, generation, page, outcome)

    def _guard(self, epoch: int) -> None:
        """Called before every write."""
        with self._lock:
            live = epoch == self._epoch
        if not live:
            raise _Abort("stale")
        if not self._can_edit():
            raise _Abort("cannot_edit")

    def _import(self, epoch: int, page: PageSpec) -> None:
        self._guard(epoch)
        pages = self._perks.pages()
        managed = next((p for p in pages if p.is_editable and p.name.startswith(MANAGED_PAGE_PREFIX)), None)
        body = PageBody(
            managed.name if managed is not None else MANAGED_PAGE_NAME,
            page.primary_style_id,
            page.sub_style_id,
            page.perk_ids,
        )
        if managed is not None:
            self._guard(epoch)
            self._perks.update_page(managed.id, body)
            page_id = managed.id
        else:
            owned = self._perks.owned_page_count()
            if sum(1 for p in pages if p.is_custom) >= owned:
                raise _Abort("no_free_page")
            self._guard(epoch)
            page_id = self._perks.create_page(body).id
        current = self._perks.current_page()
        if current.id != page_id:
            self._guard(epoch)
            self._perks.set_current(page_id)
            current = self._perks.current_page()
        stored = PageSpec(current.primary_style_id, current.sub_style_id, current.selected_perk_ids)
        if current.id != page_id or not current.current or stored != page:
            raise _Abort("not_confirmed")

    def _finish(self, epoch: int, generation: int, page: PageSpec, outcome: str | None) -> None:
        with self._lock:
            if epoch != self._epoch:
                return  # Answer for a session that no longer exists.
            self._in_flight = None
            if outcome is None:
                if generation > self._applied_generation:
                    self._applied = page
                    self._applied_generation = generation
                if generation == self._chosen_generation:
                    self._error = None
            else:
                self._error = outcome
            newer = self._chosen is not None and self._chosen_generation > generation
            if newer and self._timer is None:
                self._send()
            snapshot = self._snapshot()
        self._notify(snapshot)

    def _notify(self, snapshot: RuneImportSnapshot) -> RuneImportSnapshot:
        if self._on_change is not None:
            try:
                self._on_change(snapshot)
            except Exception:
                log.exception("[RUNES] snapshot listener failed")
        return snapshot
