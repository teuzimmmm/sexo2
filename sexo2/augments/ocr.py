"""Reading the card titles with the Windows OCR (decision D-115).

The title of each card is read with ``Windows.Media.Ocr`` (built into Windows 10/11,
no model shipped with SEXO2) and matched against the names of the current mode's
pool, in the client's language. A title that matches no name closely enough leaves
the card to the icon matcher. Measured on the reference captures, the title (one or
two lines) sits between 0.372·H and 0.428·H; the category tag below it is left out.
"""

from __future__ import annotations

import difflib
import io
import unicodedata
from typing import Callable

from PIL import Image, ImageOps

from sexo2.augments.catalog import Catalog
from sexo2.augments.offers import CardRead
from sexo2.augments.vision import Layout

TITLE_TOP = 0.372
TITLE_BOTTOM = 0.428
TITLE_INSET = 0.06  # of the card width, keeps the frame out


def title_boxes(width: int, height: int, layout: Layout = Layout()) -> list[tuple[int, int, int, int]]:
    boxes = []
    for left, _top, right, _bottom in layout.cards(width, height):
        inset = round(TITLE_INSET * (right - left))
        boxes.append((left + inset, round(TITLE_TOP * height), right - inset, round(TITLE_BOTTOM * height)))
    return boxes


def normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c if c.isalnum() else " " for c in decomposed if not unicodedata.combining(c)).split())


def match_name(text: str, catalog: Catalog, *, min_ratio: float = 0.8) -> CardRead:
    """The pool augment whose name the read title matches, or an unknown read."""
    seen = normalise(text)
    if not seen:
        return CardRead(None, 0.0)
    scored = sorted(
        ((difflib.SequenceMatcher(None, seen, normalise(a.name)).ratio(), a.id) for a in catalog.augments),
        reverse=True,
    )
    if not scored or scored[0][0] < min_ratio:
        return CardRead(None, scored[0][0] if scored else 0.0)
    if len(scored) > 1 and scored[1][0] >= scored[0][0] - 0.05:
        return CardRead(None, scored[0][0])  # two names read alike: leave it to the icon
    return CardRead(scored[0][1], scored[0][0])


def prepare(title: Image.Image) -> Image.Image:
    """Light text on a dark card: grey, inverted, enlarged to about 48 px of text height."""
    grey = ImageOps.invert(ImageOps.grayscale(title.convert("RGB")))
    scale = max(1.0, 96 / max(1, grey.height))
    return grey.resize((round(grey.width * scale), round(grey.height * scale)), Image.Resampling.LANCZOS)


UNAVAILABLE_REASON = ""


def windows_reader() -> Callable[[Image.Image], str] | None:
    """A function reading the text of an image with the Windows OCR, or None when unavailable.

    The user's profile languages come first; otherwise any OCR language installed on Windows.
    """
    global UNAVAILABLE_REASON
    try:
        import asyncio

        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
    except Exception as error:
        UNAVAILABLE_REASON = f"import: {error}"
        return None
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        for language in OcrEngine.available_recognizer_languages:
            engine = OcrEngine.try_create_from_language(language)
            if engine is not None:
                break
    if engine is None:
        UNAVAILABLE_REASON = "no OCR language installed"
        return None

    async def recognise(png: bytes) -> str:
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(png)
        await writer.store_async()
        writer.detach_stream()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
        return result.text

    loop = asyncio.new_event_loop()  # one for every reading; the reader stays on the thread that made it

    def read(image: Image.Image) -> str:
        buffer = io.BytesIO()
        prepare(image).save(buffer, format="PNG")
        return loop.run_until_complete(recognise(buffer.getvalue()))

    return read


def read_titles(
    frame: Image.Image,
    reader: Callable[[Image.Image], str],
    catalog: Catalog,
    layout: Layout = Layout(),
    *,
    screen: tuple[int, int] | None = None,
    origin: tuple[int, int] = (0, 0),
) -> list[CardRead]:
    """One read per card from its title (``frame`` may be the card area, as in vision.read_offer)."""
    reads = []
    for left, top, right, bottom in title_boxes(*(screen or frame.size), layout):
        crop = frame.crop((left - origin[0], top - origin[1], right - origin[0], bottom - origin[1]))
        try:
            reads.append(match_name(reader(crop), catalog))
        except Exception:
            reads.append(CardRead(None, 0.0))
    return reads


def combine(by_title: list[CardRead], by_icon: list[CardRead]) -> list[CardRead]:
    """The title wins when it names a card; otherwise the icon reading stands."""
    return [t if t.augment_id is not None else i for t, i in zip(by_title, by_icon)]
