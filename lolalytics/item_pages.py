"""Pure packing of build suggestions into explicitly budgeted item pages."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import math
from typing import Any

from .builds import BuildPage, ItemBlock, ItemChoice
from .errors import QueryError


@dataclass
class PreparedItemBlock:
    label: str
    block: ItemBlock
    source: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PreparedItemPage:
    title: str
    blocks: list[PreparedItemBlock]

    def to_dict(self) -> dict:
        return asdict(self)


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QueryError(f"build page {field} must be a non-empty string")
    return value


def _identity(page: BuildPage) -> tuple[str, str, str, str, str, str]:
    query = page.query
    resolved = page.resolved
    if not isinstance(query, dict):
        raise QueryError("build page query must be an object")
    if not isinstance(resolved, dict):
        raise QueryError("build page resolved metadata must be an object")
    champion = _nonempty_string(query.get("champion", resolved.get("champion")), "champion")
    resolved_champion = resolved.get("champion")
    if resolved_champion is not None and resolved_champion != champion:
        raise QueryError("build page query and resolved champion do not match")

    mode = _nonempty_string(query.get("mode", resolved.get("mode")), "mode")
    resolved_mode = resolved.get("mode")
    if resolved_mode is not None and resolved_mode != mode:
        raise QueryError("build page query and resolved mode do not match")

    query_patch = query.get("patch")
    resolved_patch = resolved.get("patch")
    if query_patch is not None and resolved_patch is not None and query_patch != resolved_patch:
        raise QueryError("build page query and resolved patch do not match")
    patch = _nonempty_string(resolved_patch or query_patch, "patch")

    tier = _nonempty_string(query.get("tier", resolved.get("tier")), "tier")
    region = _nonempty_string(query.get("region", resolved.get("region")), "region")
    if resolved.get("tier") is not None and resolved["tier"] != tier:
        raise QueryError("build page query and resolved tier do not match")
    if resolved.get("region") is not None and resolved["region"] != region:
        raise QueryError("build page query and resolved region do not match")
    lane = resolved.get("effective_lane") or resolved.get("lane") or query.get("lane")
    lane = _nonempty_string(lane, "effective lane")
    query_lane = query.get("lane")
    if query_lane not in (None, "all", lane):
        raise QueryError("build page query and effective lane do not match")
    return champion, mode, patch, tier, region, lane


def _suggestion_label(page: BuildPage) -> str:
    if page.selection == "win":
        return "WR"
    if page.selection == "pick":
        return "Common"
    if page.selection in ("vs", "archetype"):
        return _nonempty_string(page.label, "matchup label")
    raise QueryError(f"unsupported build page selection: {page.selection!r}")


def _kind_label(kind: Any) -> str:
    labels = {
        "starting": "Starting",
        "core": "Core",
        "suggested_core": "Core sugerido (sem ordem)",
        "item1": "Item 1",
        "item2": "Item 2",
        "item3": "Item 3",
        "item4": "Item 4",
        "item5": "Item 5",
        "item6": "Item 6",
    }
    if not isinstance(kind, str) or not kind:
        raise QueryError("item block kind must be a non-empty string")
    return labels.get(kind, kind.replace("_", " ").title())


def _conditioning(page: BuildPage) -> str:
    # Compatibility for older/synthetic BuildPage instances; new factories
    # provide this field explicitly and it remains authoritative.
    value = getattr(page, "conditioning", None)
    if value is None:
        value = "opponent" if page.selection == "vs" else "keystone"
    if value == "archetype" and page.selection == "archetype" and page.query.get("mode") == "mayhem":
        return value
    if value == "mode" and page.selection in ("win", "pick") and page.query.get("mode") == "swift":
        return value
    if value not in ("keystone", "opponent"):
        raise QueryError("build page conditioning must be keystone or opponent")
    if page.selection == "vs" and value != "opponent":
        raise QueryError("matchup suggestions must use opponent conditioning")
    if page.selection in ("win", "pick") and value != "keystone":
        raise QueryError("general suggestions must use keystone conditioning")
    return value


def _source(page: BuildPage) -> dict:
    conditioning = _conditioning(page)
    return {
        "selection": page.selection,
        "label": page.label,
        "title": page.title,
        "query": deepcopy(page.query),
        "resolved": deepcopy(page.resolved),
        "source_url": page.source_url,
        "collected_at": page.collected_at,
        "cache_hit": page.cache_hit,
        "warnings": deepcopy(page.warnings),
        "conditioning": conditioning,
        "scope": f"{conditioning}_conditioned",
        "core_metrics": deepcopy(page.core_metrics),
        "matchup_metrics": deepcopy(getattr(page, "matchup_metrics", None)),
    }


def plan_item_pages(
    pages: list[BuildPage], *, max_pages: int = 1, max_blocks_per_page: int = 20
) -> list[PreparedItemPage]:
    """Pack every supplied suggestion block without dropping or merging data."""
    if not isinstance(pages, list) or not pages:
        raise QueryError("pages must be a non-empty list of build pages")
    if len(pages) > 20:
        raise QueryError("at most 20 suggestions can be planned at once")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 20:
        raise QueryError("max_pages must be an integer from 1 to 20")
    if (
        isinstance(max_blocks_per_page, bool)
        or not isinstance(max_blocks_per_page, int)
        or not 1 <= max_blocks_per_page <= 100
    ):
        raise QueryError("max_blocks_per_page must be an integer from 1 to 100")

    identity = None
    validated: list[tuple[BuildPage, str, list[str]]] = []
    champion = ""
    champion_title = ""
    total_blocks = 0
    for page in pages:
        if not isinstance(page, BuildPage):
            raise QueryError("every suggestion must be a BuildPage")
        current = _identity(page)
        if identity is None:
            identity = current
            champion = current[0]
            display = page.resolved.get("champion_name")
            champion_title = (
                display.strip() if isinstance(display, str) and display.strip() else champion.replace("-", " ").title()
            )
        elif current != identity:
            fields = ("champion", "mode", "patch", "tier", "region", "effective lane")
            different = next(name for name, left, right in zip(fields, identity, current) if left != right)
            raise QueryError(f"cannot combine build suggestions with different {different}")
        if not isinstance(page.blocks, list):
            raise QueryError("build page blocks must be a list")
        if not page.blocks:
            raise QueryError("each build suggestion must contain item blocks")
        suggestion = _suggestion_label(page)
        labels = []
        for block in page.blocks:
            if not isinstance(block, ItemBlock):
                raise QueryError("every item block must be an ItemBlock")
            if not isinstance(block.choices, list) or not block.choices:
                raise QueryError("item blocks must contain at least one choice")
            labels.append(f"{suggestion} · {_kind_label(block.kind)}")
        total_blocks += len(page.blocks)
        validated.append((page, suggestion, labels))

    if total_blocks == 0:
        raise QueryError("build suggestions contain no item blocks")
    required_pages = math.ceil(total_blocks / max_blocks_per_page)
    if required_pages > max_pages:
        raise QueryError(f"item blocks require {required_pages} pages, exceeding max_pages={max_pages}")

    entries: list[PreparedItemBlock] = []
    for page, _suggestion, labels in validated:
        source = _source(page)
        entries.extend(
            PreparedItemBlock(label=label, block=deepcopy(block), source=deepcopy(source))
            for label, block in zip(labels, page.blocks)
        )

    result = []
    for page_index, start in enumerate(range(0, len(entries), max_blocks_per_page), start=1):
        page_blocks = entries[start : start + max_blocks_per_page]
        title = f"Builds de {champion_title}"
        if required_pages > 1:
            title += f" · {page_index}/{required_pages}"
        result.append(PreparedItemPage(title=title, blocks=page_blocks))
    return result


# --------------------------------------------------------------------------
# Assistant page: one page, up to three groups of three sections each.
#
# For each recommendation the first section is the purchase sequence: the
# observed core trio in its observed order (for the matchup recommendation,
# the item1-3 picks of that summary), then one item for each of the later
# slots 4, 5 and 6. Those slots only have per-slot (marginal) observations,
# so each slot is chosen by the recommendation's own criterion among the
# choices with at least ``min_games`` games: highest win rate for the "win"
# and matchup recommendations, most games for "pick". When no choice reaches
# the minimum, the slot's most played choice is used. Items already in the
# sequence are skipped. The sequence is never a six-item build observed as a
# whole; its block keeps the metrics of every pick in ``source``.
#
# Titles are the approved ones (docs/produto/decisoes.md): the general
# recommendations show the win rate and games of the core trio, the matchup
# recommendation those of the champion against the opponent.

STARTING_TITLE = "Itens iniciais"
ALTERNATIVES_TITLE = "Alternativas"


def format_rate(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",") + "%"


def format_games(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " partidas"


def _metrics_title(metrics: dict | None, decimals: int) -> str:
    metrics = metrics or {}
    parts = []
    if isinstance(metrics.get("win_rate"), (int, float)):
        parts.append(format_rate(metrics["win_rate"], decimals))
    if isinstance(metrics.get("games"), int):
        parts.append(format_games(metrics["games"]))
    return " — ".join(parts)


def _slot_pick(block: ItemBlock, taken: set[str], criterion: str, min_games: int) -> ItemChoice | None:
    free = [choice for choice in block.choices if choice.identifier not in taken]
    if not free:
        return None

    def games(choice: ItemChoice) -> int:
        value = choice.metrics.get("games")
        return value if isinstance(value, int) else -1

    eligible = [choice for choice in free if games(choice) >= min_games]
    if not eligible:
        return max(free, key=games)
    if criterion == "pick":
        return max(eligible, key=games)
    return max(
        eligible, key=lambda c: (c.metrics.get("win_rate") is not None, c.metrics.get("win_rate") or 0, games(c))
    )


def _group(page: BuildPage, title: str, min_games: int) -> list[PreparedItemBlock]:
    by_kind = {block.kind: block for block in page.blocks}
    criterion = "pick" if page.selection == "pick" else "win"
    head_kinds = ("item1", "item2", "item3") if page.selection == "vs" else ("core",)
    sequence: list[ItemChoice] = []
    picks: list[dict] = []
    for kind in head_kinds:
        block = by_kind.get(kind)
        for choice in block.choices if block else []:
            if choice.identifier not in {c.identifier for c in sequence}:
                sequence.append(choice)
                picks.append({"slot": kind, "id": choice.identifier, "metrics": deepcopy(choice.metrics)})
    for kind in ("item4", "item5", "item6"):
        block = by_kind.get(kind)
        if block is None:
            continue
        choice = _slot_pick(block, {c.identifier for c in sequence}, criterion, min_games)
        if choice is not None:
            sequence.append(choice)
            picks.append({"slot": kind, "id": choice.identifier, "metrics": deepcopy(choice.metrics)})
    if not sequence:
        return []
    source = _source(page)
    source["sequence_rule"] = {
        "head": list(head_kinds),
        "later_slots": criterion,
        "min_games": min_games,
        "picks": picks,
    }
    blocks = [
        PreparedItemBlock(
            label=title,
            block=ItemBlock("sequence", [ItemChoice(c.identifier, 1, {}, {}) for c in sequence], {}, "", True),
            source=deepcopy(source),
        )
    ]
    starting = by_kind.get("starting")
    if starting is not None and starting.choices:
        blocks.append(PreparedItemBlock(label=STARTING_TITLE, block=deepcopy(starting), source=deepcopy(source)))
    used = {c.identifier for c in sequence}
    alternatives: list[ItemChoice] = []
    for kind in ("item4", "item5", "item6"):
        for choice in by_kind[kind].choices if kind in by_kind else []:
            if choice.identifier not in used:
                used.add(choice.identifier)
                alternatives.append(ItemChoice(choice.identifier, 1, deepcopy(choice.metrics), {}))
    if alternatives:
        blocks.append(
            PreparedItemBlock(
                label=ALTERNATIVES_TITLE,
                block=ItemBlock("alternatives", alternatives, {}, "", False),
                source=deepcopy(source),
            )
        )
    return blocks


def _display_name(resolved: dict, key: str, slug: str) -> str:
    name = resolved.get(key)
    return name.strip() if isinstance(name, str) and name.strip() else slug.replace("-", " ").title()


def plan_assistant_page(
    win: BuildPage | None,
    pick: BuildPage | None,
    matchup: BuildPage | None = None,
    *,
    min_games: int = 100,
) -> PreparedItemPage:
    """The single assistant page: highest win rate, most played, then the matchup group."""
    groups = [(page, kind) for page, kind in ((win, "win"), (pick, "pick"), (matchup, "vs")) if page is not None]
    if not groups:
        raise QueryError("at least one build suggestion is required")
    champion = None
    for page, kind in groups:
        if not isinstance(page, BuildPage) or page.selection != kind:
            raise QueryError(f"expected a {kind!r} build suggestion")
        identity = _identity(page)
        if champion is None:
            champion = identity[0]
            champion_title = _display_name(page.resolved, "champion_name", champion)
        elif identity[0] != champion:
            raise QueryError("cannot combine build suggestions of different champions")

    blocks: list[PreparedItemBlock] = []
    if win is not None:
        blocks += _group(win, _metrics_title(win.core_metrics, 1), min_games)
    if pick is not None:
        blocks += _group(pick, _metrics_title(pick.core_metrics, 1), min_games)
    if matchup is not None:
        opponent = _display_name(matchup.resolved, "opponent_name", str(matchup.query.get("opponent") or ""))
        metrics = _metrics_title(matchup.matchup_metrics, 2)
        title = f"Counter {opponent}" + (f" — {metrics}" if metrics else "")
        blocks += _group(matchup, title, min_games)
    if not blocks:
        raise QueryError("build suggestions contain no items")
    return PreparedItemPage(title=champion_title, blocks=blocks)
