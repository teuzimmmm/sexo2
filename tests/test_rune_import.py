"""RuneImportController: deterministic executor, scheduler and fake client."""

import json
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from lcu.features.lcu_perks import PageBody, PerksError, RunePage
from sexo2.services.rune_import import MANAGED_PAGE_NAME, RuneImportController, SerialExecutor, SessionKey
from sexo2.services.rune_rules import PageSpec, StyleCatalog

FIXTURE = Path(__file__).parent / "fixtures" / "lcu" / "perks-styles-representative.json"
CATALOG = StyleCatalog.from_payload(json.loads(FIXTURE.read_text())["styles"])

ELECTROCUTE = PageSpec(8100, 8200, (8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001))
DARK_HARVEST = PageSpec(8100, 8200, (8128, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001))
HAIL = PageSpec(8100, 8200, (9923, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001))
INVALID = PageSpec(8100, 8100, ELECTROCUTE.perk_ids)
AHRI = SessionKey("game-1", 103)
ANNIE = SessionKey("game-1", 1)


def page(page_id, name, *, editable=True, deletable=True, current=False, spec=ELECTROCUTE):
    return RunePage(
        page_id, name, editable, deletable, False, current, spec.primary_style_id, spec.sub_style_id, spec.perk_ids
    )


PERSONAL = page(50, "Minha Ahri", spec=HAIL)
DEFAULT = page(1, "Domination", editable=False, deletable=False, current=True, spec=DARK_HARVEST)


class FakePerks:
    """Client state with recorded writes. ``hooks`` run before a write is applied."""

    def __init__(self, pages=(DEFAULT, PERSONAL), owned=2):
        self.pages_by_id = {p.id: p for p in pages}
        self.owned = owned
        self.writes = []
        self.hooks = []
        self.fail_next = None
        self.store_override = None
        self.next_id = 100

    def _before_write(self, call):
        while self.hooks:
            self.hooks.pop(0)()
        if self.fail_next is not None:
            error, self.fail_next = self.fail_next, None
            raise error
        self.writes.append(call)

    def _store(self, page_id, body):
        spec = self.store_override or PageSpec(body.primary_style_id, body.sub_style_id, body.selected_perk_ids)
        self.pages_by_id[page_id] = page(page_id, body.name, spec=spec)

    def pages(self):
        return list(self.pages_by_id.values())

    def current_page(self):
        return next(p for p in self.pages_by_id.values() if p.current)

    def owned_page_count(self):
        return self.owned

    def create_page(self, body: PageBody):
        self._before_write(("POST", body))
        page_id, self.next_id = self.next_id, self.next_id + 1
        self._store(page_id, body)
        self._make_current(page_id)
        return self.pages_by_id[page_id]

    def update_page(self, page_id, body: PageBody):
        self._before_write(("PUT", page_id, body))
        was_current = self.pages_by_id[page_id].current
        self._store(page_id, body)
        if was_current:
            self._make_current(page_id)

    def set_current(self, page_id):
        self._before_write(("CURRENT", page_id))
        self._make_current(page_id)

    def _make_current(self, page_id):
        for key, value in list(self.pages_by_id.items()):
            self.pages_by_id[key] = replace(value, current=key == page_id)


class ManualExecutor:
    def __init__(self):
        self.jobs = []

    def submit(self, work):
        self.jobs.append(work)
        return True

    def run_all(self):
        while self.jobs:
            self.jobs.pop(0)()


class FakeScheduler:
    def __init__(self):
        self.now = 0.0
        self.timers = []

    def call_later(self, delay, callback):
        timer = _Timer(self.now + delay, callback)
        self.timers.append(timer)
        return timer

    def advance(self, seconds):
        self.now += seconds
        for timer in [t for t in self.timers if t.due <= self.now and not t.cancelled]:
            timer.cancelled = True
            timer.callback()


class _Timer:
    def __init__(self, due, callback):
        self.due, self.callback, self.cancelled = due, callback, False

    def cancel(self):
        self.cancelled = True


class ControllerTestCase(unittest.TestCase):
    def setUp(self):
        self.perks = FakePerks()
        self.executor = ManualExecutor()
        self.scheduler = FakeScheduler()
        self.editable = True
        self.controller = RuneImportController(
            self.perks,
            can_edit=lambda: self.editable,
            executor=self.executor,
            scheduler=self.scheduler,
            debounce=0.3,
        )
        self.controller.set_catalog(CATALOG)
        self.controller.set_session(AHRI)

    def personal_pages_untouched(self):
        self.assertEqual(self.perks.pages_by_id[PERSONAL.id], PERSONAL)
        self.assertEqual(replace(self.perks.pages_by_id[DEFAULT.id], current=True), DEFAULT)
        self.assertFalse(any(call[0] == "PUT" and call[1] in (PERSONAL.id, DEFAULT.id) for call in self.perks.writes))


class ChooseTests(ControllerTestCase):
    def test_display_does_not_import(self):
        snapshot = self.controller.display([ELECTROCUTE, HAIL])
        self.assertEqual(snapshot.displayed, (ELECTROCUTE, HAIL))
        self.assertEqual(self.executor.jobs, [])

    def test_choosing_imports_immediately_and_confirms_by_read_back(self):
        snapshot = self.controller.choose(ELECTROCUTE)
        self.assertTrue(snapshot.pending)
        self.assertEqual(len(self.executor.jobs), 1)
        self.executor.run_all()
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot.applied, ELECTROCUTE)
        self.assertFalse(snapshot.pending)
        self.assertIsNone(snapshot.error)
        self.assertEqual([call[0] for call in self.perks.writes], ["POST"])
        created = self.perks.current_page()
        self.assertEqual(created.name, MANAGED_PAGE_NAME)
        self.personal_pages_untouched()

    def test_managed_page_is_reused_instead_of_creating_another(self):
        self.perks.pages_by_id[60] = page(60, "SEXO2", spec=HAIL)
        self.perks.owned = 2  # full: personal + managed
        self.controller.choose(ELECTROCUTE)
        self.executor.run_all()
        self.assertEqual([call[:2] for call in self.perks.writes], [("PUT", 60), ("CURRENT", 60)])
        self.assertEqual(self.controller.snapshot().applied, ELECTROCUTE)
        self.assertEqual(sum(1 for p in self.perks.pages() if p.name.startswith("SEXO2")), 1)
        self.personal_pages_untouched()

    def test_full_inventory_without_managed_page_never_touches_personal_pages(self):
        self.perks.owned = 1
        self.controller.choose(ELECTROCUTE)
        self.executor.run_all()
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot.error, "no_free_page")
        self.assertIsNone(snapshot.applied)
        self.assertEqual(self.perks.writes, [])
        self.personal_pages_untouched()

    def test_invalid_page_is_rejected_and_never_sent(self):
        snapshot = self.controller.choose(INVALID)
        self.assertEqual(snapshot.error, "invalid_page")
        self.assertEqual([v.code for v in snapshot.violations], ["sub_style_same_as_primary"])
        self.assertEqual(self.executor.jobs, [])
        snapshot = self.controller.edit(INVALID)
        self.scheduler.advance(1)
        self.assertEqual(self.executor.jobs, [])
        self.assertEqual(self.perks.writes, [])

    def test_failure_keeps_last_confirmed_page(self):
        self.controller.choose(ELECTROCUTE)
        self.executor.run_all()
        self.perks.fail_next = PerksError("rejected", "boom", status=500)
        self.controller.choose(HAIL)
        self.executor.run_all()
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot.error, "lcu_rejected")
        self.assertEqual(snapshot.applied, ELECTROCUTE)
        self.assertEqual(snapshot.chosen, HAIL)

    def test_read_back_mismatch_is_not_confirmed(self):
        self.perks.store_override = DARK_HARVEST  # the client stores something else
        self.controller.choose(ELECTROCUTE)
        self.executor.run_all()
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot.error, "not_confirmed")
        self.assertIsNone(snapshot.applied)

    def test_cannot_edit_sends_nothing_and_keeps_applied(self):
        self.controller.choose(ELECTROCUTE)
        self.executor.run_all()
        writes = list(self.perks.writes)
        self.editable = False
        self.controller.choose(HAIL)
        self.executor.run_all()
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot.error, "cannot_edit")
        self.assertEqual(snapshot.applied, ELECTROCUTE)
        self.assertEqual(self.perks.writes, writes)

    def test_editing_locked_mid_import_stops_before_the_next_write(self):
        self.perks.pages_by_id[60] = page(60, "SEXO2", spec=HAIL)
        self.perks.hooks.append(lambda: setattr(self, "editable", False))
        self.controller.choose(ELECTROCUTE)
        self.executor.run_all()
        self.assertEqual([call[0] for call in self.perks.writes], ["PUT"])  # no CURRENT after the lock
        self.assertEqual(self.controller.snapshot().error, "cannot_edit")


class EditTests(ControllerTestCase):
    def test_edits_are_debounced_and_coalesced(self):
        self.controller.edit(ELECTROCUTE)
        self.scheduler.advance(0.2)
        self.controller.edit(DARK_HARVEST)
        self.scheduler.advance(0.2)
        self.assertEqual(self.executor.jobs, [])
        self.assertTrue(self.controller.snapshot().pending)
        self.scheduler.advance(0.1)
        self.assertEqual(len(self.executor.jobs), 1)
        self.executor.run_all()
        self.assertEqual(self.controller.snapshot().applied, DARK_HARVEST)
        self.assertEqual(len([call for call in self.perks.writes if call[0] in ("POST", "PUT")]), 1)

    def test_one_write_in_flight_then_only_the_newest_choice(self):
        self.controller.choose(ELECTROCUTE)
        self.controller.edit(DARK_HARVEST)
        self.scheduler.advance(0.3)
        self.controller.edit(HAIL)
        self.scheduler.advance(0.3)
        self.assertEqual(len(self.executor.jobs), 1)  # still only the first import
        self.executor.run_all()
        bodies = [call[-1] for call in self.perks.writes if call[0] in ("POST", "PUT")]
        self.assertEqual([body.selected_perk_ids[0] for body in bodies], [8112, 9923])
        self.assertEqual(self.controller.snapshot().applied, HAIL)

    def test_confirm_forces_the_send(self):
        self.controller.edit(HAIL)
        self.controller.confirm()
        self.assertEqual(len(self.executor.jobs), 1)
        self.scheduler.advance(1)
        self.executor.run_all()
        self.assertEqual(self.controller.snapshot().applied, HAIL)
        self.assertEqual(len([call for call in self.perks.writes if call[0] in ("POST", "PUT")]), 1)

    def test_back_drops_unsent_edits_and_keeps_applied(self):
        self.controller.choose(ELECTROCUTE)
        self.executor.run_all()
        self.controller.edit(HAIL)
        snapshot = self.controller.back()
        self.scheduler.advance(1)
        self.executor.run_all()
        self.assertEqual(snapshot.applied, ELECTROCUTE)
        self.assertIsNone(snapshot.chosen)
        self.assertFalse(snapshot.pending)
        self.assertEqual(len([call for call in self.perks.writes if call[0] in ("POST", "PUT")]), 1)


class SessionTests(ControllerTestCase):
    def test_late_answer_from_previous_champion_is_ignored(self):
        self.perks.hooks.append(lambda: self.controller.set_session(ANNIE))
        self.controller.choose(ELECTROCUTE)
        self.controller.edit(HAIL)
        self.executor.run_all()
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot.session, ANNIE)
        self.assertIsNone(snapshot.applied)
        self.assertIsNone(snapshot.chosen)
        self.assertFalse(snapshot.pending)
        # The write already in flight finishes; the newer Ahri edit never follows it.
        self.assertEqual([call[0] for call in self.perks.writes], ["POST"])
        self.assertEqual(self.perks.writes[0][1].selected_perk_ids[0], 8112)

    def test_session_change_before_the_worker_starts_writes_nothing(self):
        self.controller.choose(ELECTROCUTE)
        self.controller.set_session(ANNIE)
        self.executor.run_all()
        self.assertEqual(self.perks.writes, [])
        self.assertIsNone(self.controller.snapshot().error)

    def test_session_change_drops_pending_debounce(self):
        self.controller.edit(HAIL)
        self.controller.set_session(ANNIE)
        self.scheduler.advance(1)
        self.assertEqual(self.executor.jobs, [])

    def test_leaving_champion_select_stops_follow_up_writes(self):
        self.controller.choose(ELECTROCUTE)
        self.controller.edit(HAIL)
        self.controller.confirm()  # queued behind the running import
        self.perks.hooks.append(lambda: self.controller.set_session(None))
        self.executor.run_all()
        bodies = [call[-1] for call in self.perks.writes if call[0] in ("POST", "PUT")]
        self.assertEqual([body.selected_perk_ids[0] for body in bodies], [8112])
        self.assertEqual(self.controller.snapshot().error, None)

    def test_new_session_can_import_after_old_answer_arrives(self):
        self.controller.choose(ELECTROCUTE)
        self.controller.set_session(ANNIE)
        self.controller.choose(HAIL)
        self.executor.run_all()  # old job aborts as stale; new one runs
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot.applied, HAIL)
        bodies = [call[-1] for call in self.perks.writes if call[0] in ("POST", "PUT")]
        self.assertEqual([body.selected_perk_ids[0] for body in bodies], [9923])

    def test_choose_without_session_or_catalog_is_an_error(self):
        self.controller.set_session(None)
        self.assertEqual(self.controller.choose(ELECTROCUTE).error, "no_session")
        self.controller.set_session(AHRI)
        self.controller.set_catalog(None)
        self.assertEqual(self.controller.choose(ELECTROCUTE).error, "catalog_unavailable")
        self.assertEqual(self.executor.jobs, [])


class ProductionWiringTests(unittest.TestCase):
    def test_default_worker_and_timer_apply_an_edit(self):
        done = threading.Event()
        perks = FakePerks()
        executor = SerialExecutor("SEXO2-Rune-import-test")
        controller = RuneImportController(
            perks,
            can_edit=lambda: True,
            executor=executor,
            debounce=0.01,
            on_change=lambda snapshot: snapshot.applied == HAIL and done.set(),
        )
        controller.set_catalog(CATALOG)
        controller.set_session(AHRI)
        controller.edit(HAIL)
        self.assertTrue(done.wait(5))
        self.assertTrue(executor.close())


if __name__ == "__main__":
    unittest.main()
