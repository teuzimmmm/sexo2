"""Allowlisted display protocol for the isolated native renderer, without LCU data."""
import json
import unicodedata

MAX_BYTES = 256 * 1024  # Includes the JSON Lines terminator.
MAX_CARDS = 16
MAX_LINES = 256
MAX_TEXT = 512
MAX_SEQUENCE = 2**53 - 1


class ProtocolError(ValueError):
    """The display projection is incompatible; never include source data in errors."""


def _text(value):
    if (not isinstance(value, str) or len(value) > MAX_TEXT
            or any(unicodedata.category(c).startswith('C') for c in value)):
        raise ProtocolError('Invalid display text.')
    return value


def encode(frame, sequence, *, ttl_ms=8000):
    """Encode one bounded frame. Context validation remains with OverlayRuntime.

    Sequence increases within each child process. TTL starts on receipt and never
    permits extending the producer's existing freshness checks. Inactive frames
    discard their view rather than sending hidden/stale content to the renderer.
    """
    if type(sequence) is not int or not 1 <= sequence <= MAX_SEQUENCE:
        raise ProtocolError('Invalid frame sequence.')
    if type(ttl_ms) is not int or not 1 <= ttl_ms <= 8000:
        raise ProtocolError('Invalid frame lifetime.')
    if type(frame.active) is not bool or type(frame.preview) is not bool:
        raise ProtocolError('Invalid frame state.')
    cards, selected = [], 0
    if frame.active:
        if len(frame.view.cards) > MAX_CARDS:
            raise ProtocolError('Too many display cards.')
        selected = frame.view.selected
        if type(selected) is not int or not 0 <= selected < max(1, len(frame.view.cards)):
            raise ProtocolError('Invalid selected card.')
        for card in frame.view.cards:
            if len(card.lines) > MAX_LINES:
                raise ProtocolError('Too many display lines.')
            cards.append({'title': _text(card.title), 'lines': [_text(x) for x in card.lines]})
    payload = {'v': 1, 'seq': sequence, 'ttlMs': ttl_ms, 'active': frame.active,
               'preview': frame.preview, 'selected': selected, 'cards': cards}
    encoded = (json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    if len(encoded) > MAX_BYTES:
        raise ProtocolError('Display frame exceeds byte limit.')
    return encoded
