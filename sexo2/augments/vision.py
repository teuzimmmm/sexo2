"""Where the augment cards are on screen and which augment each one shows.

Layout: the three cards are centred horizontally on the game window and scale
with its height H. The fractions are those measured by ARAM Mayhem Tracker
(Sygnano/aram-mayhem-tracker, MIT, crates/mayhem-vision) on real captures
from 1024x768 to 3440x1440: card centres at W/2 + (-0.3346, 0.0062, 0.3470)·H,
card top at 0.1793·H, card size 0.2949·H by 0.4871·H. The icon sits in the
upper part of the card; its box below was measured here on the same captures.
Everything is configurable because the HUD scale or a future client change can
move it.

Recognition compares the icon area with the icons of the current mode's pool
(normalised cross-correlation on small grey images, Pillow only). A card is
named only when the best match is good enough and clearly closer than the second;
otherwise it stays unknown and the player can name it by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from PIL import Image, ImageStat

from sexo2.augments.offers import CardRead


@dataclass(frozen=True)
class Layout:
    centres: tuple[float, ...] = (-0.3346, 0.0062, 0.3470)
    card_top: float = 0.1793
    card_width: float = 0.2949
    card_height: float = 0.4871
    # Icon box inside a card, as fractions of H from the card's centre/top.
    icon_top: float = 0.040
    icon_height: float = 0.135
    icon_width: float = 0.135

    def cards(self, width: int, height: int) -> list[tuple[int, int, int, int]]:
        """Card boxes (left, top, right, bottom) in pixels."""
        boxes = []
        for centre in self.centres:
            cx = width / 2 + centre * height
            half = self.card_width * height / 2
            top = self.card_top * height
            boxes.append((round(cx - half), round(top), round(cx + half), round(top + self.card_height * height)))
        return boxes

    def icons(self, width: int, height: int) -> list[tuple[int, int, int, int]]:
        boxes = []
        for left, top, right, _bottom in self.cards(width, height):
            cx = (left + right) / 2
            half = self.icon_width * height / 2
            y = top + self.icon_top * height
            boxes.append((round(cx - half), round(y), round(cx + half), round(y + self.icon_height * height)))
        return boxes


# Arena cards sit slightly higher and closer together; measured on a 1920x1080
# capture of an Arena offer (cards at x 447-763, 801-1118, 1155-1472, y 181-693;
# icon at y 250-380).
ARENA_LAYOUT = Layout(
    centres=(-0.3287, 0.0, 0.3273),
    card_top=0.1676,
    card_width=0.2935,
    card_height=0.4741,
    icon_top=0.060,
    icon_height=0.125,
)


SIZE = 32


def signature(image: Image.Image, background: tuple[int, int, int] = (8, 28, 32)) -> list[float]:
    """Zero-mean, unit-length colour vector of an icon (transparency over the card background).

    Colour matters: some silver and gold augments share the same drawing in a different tint.
    """
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        base = Image.new("RGBA", image.size, (*background, 255))
        image = Image.alpha_composite(base, image)
    small = image.convert("RGB").resize((SIZE, SIZE), Image.Resampling.BILINEAR)
    values = [channel for pixel in small.getdata() for channel in pixel]
    mean = sum(values) / len(values)
    centred = [v - mean for v in values]
    norm = sum(v * v for v in centred) ** 0.5 or 1.0
    return [v / norm for v in centred]


def similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class IconMatcher:
    """Names an icon among a closed set of templates (the current mode's pool)."""

    def __init__(self, templates: dict[int, Image.Image | list[float]], *, min_score=0.6, max_ratio=0.5) -> None:
        self._templates = {
            augment_id: t if isinstance(t, list) else signature(t) for augment_id, t in templates.items()
        }
        self._min_score = min_score
        self._max_ratio = max_ratio

    def add(self, augment_id: int, image: Image.Image) -> None:
        """Learn a template, e.g. the crop of a card the player named by hand."""
        self._templates[augment_id] = signature(image)

    def ranked(self, image: Image.Image) -> list[tuple[int, float]]:
        probe = signature(image)
        return sorted(((i, similarity(probe, t)) for i, t in self._templates.items()), key=lambda r: -r[1])

    def read(self, image: Image.Image) -> CardRead:
        ranked = self.ranked(image)
        if not ranked:
            return CardRead(None, 0.0)
        best_id, best = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else -1.0
        # Accept only a match clearly closer than the runner-up: its distance (1 - score)
        # must be at most max_ratio times the runner-up's.
        if best < self._min_score or (1 - best) > self._max_ratio * (1 - second):
            return CardRead(None, max(0.0, best))
        return CardRead(best_id, max(0.0, min(1.0, best)))


def card_area(width: int, height: int, layout: Layout = Layout()) -> tuple[int, int, int, int]:
    """The smallest box holding every card place and its top edge, to capture only that."""
    boxes = layout.cards(width, height)
    margin = max(2, round(0.01 * height))
    return (
        max(0, min(b[0] for b in boxes)),
        max(0, min(b[1] for b in boxes) - margin),
        min(width, max(b[2] for b in boxes)),
        min(height, max(b[3] for b in boxes)),
    )


def _shift(box: tuple[int, int, int, int], origin: tuple[int, int]) -> tuple[int, int, int, int]:
    return (box[0] - origin[0], box[1] - origin[1], box[2] - origin[0], box[3] - origin[1])


def _border_box(left: int, top: int, right: int, height: int) -> tuple[int, int, int, int]:
    """The thin box on a card place's top edge, where a card shows a light frame."""
    inset = round(0.1 * (right - left))
    half = max(1, round(0.006 * height))
    return (left + inset, top - half, right - inset, top + half + 1)


def border_strip(width: int, height: int, layout: Layout = Layout()) -> tuple[int, int, int, int]:
    """The thin row holding every card's top edge: about 2 % of the card area, captured
    alone while no offer is open."""
    boxes = [_border_box(left, top, right, height) for left, top, right, _bottom in layout.cards(width, height)]
    return (
        max(0, min(b[0] for b in boxes)),
        max(0, min(b[1] for b in boxes)),
        min(width, max(b[2] for b in boxes)),
        min(height, max(b[3] for b in boxes)),
    )


def borders_lit(
    strip: Image.Image,
    layout: Layout = Layout(),
    *,
    screen: tuple[int, int],
    origin: tuple[int, int],
    border_min=150,
) -> bool:
    """The first half of :func:`cards_present`, on the :func:`border_strip` alone: every card
    place shows a light top edge. Never False when cards_present is True."""
    width, height = screen
    grey = strip.convert("L")
    return all(
        ImageStat.Stat(grey.crop(_shift(_border_box(left, top, right, height), origin))).mean[0] >= border_min
        for left, top, right, _bottom in layout.cards(width, height)
    )


def cards_present(
    frame: Image.Image,
    layout: Layout = Layout(),
    *,
    screen: tuple[int, int] | None = None,
    origin: tuple[int, int] = (0, 0),
    border_min=150,
    inside_max=90,
) -> bool:
    """True when every card place shows a card: a light frame edge above a dark card face.

    ``frame`` is the whole screen, or the part of a ``screen``-sized one that starts at
    ``origin`` (see :func:`card_area`). Measured on the reference captures: card tops
    178-233 and faces 22-66 in grey level, against at most one such place on frames
    without cards (champion select, the map).
    """
    width, height = screen or frame.size
    grey = frame.convert("L")
    for left, top, right, bottom in layout.cards(width, height):
        border = grey.crop(_shift(_border_box(left, top, right, height), origin))
        face_inset = round(0.25 * (right - left))
        face = grey.crop(
            _shift(
                (
                    left + face_inset,
                    top + round(0.55 * (bottom - top)),
                    right - face_inset,
                    top + round(0.75 * (bottom - top)),
                ),
                origin,
            )
        )
        if ImageStat.Stat(border).mean[0] < border_min or ImageStat.Stat(face).mean[0] > inside_max:
            return False
    return True


def crops(
    frame: Image.Image,
    layout: Layout = Layout(),
    *,
    screen: tuple[int, int] | None = None,
    origin: tuple[int, int] = (0, 0),
) -> list[Image.Image]:
    """The icon area of each card place."""
    return [frame.crop(_shift(box, origin)) for box in layout.icons(*(screen or frame.size))]


def read_offer(
    frame: Image.Image,
    matcher: IconMatcher,
    layout: Layout = Layout(),
    *,
    screen: tuple[int, int] | None = None,
    origin: tuple[int, int] = (0, 0),
) -> list[CardRead] | None:
    """One reading for :class:`OfferTracker`: None without cards, else one read per card."""
    if not cards_present(frame, layout, screen=screen, origin=origin):
        return None
    return [matcher.read(icon) for icon in crops(frame, layout, screen=screen, origin=origin)]
