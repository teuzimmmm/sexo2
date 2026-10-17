"""Current on-screen offers; recognition certainty is separate from build risk."""
from dataclasses import dataclass
from difflib import SequenceMatcher
import math
import unicodedata

from .model import Card, View, text


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold()
                   if c.isalnum())


@dataclass(frozen=True)
class Choice:
    identifier: str | None
    name: str | None
    match: str = 'unknown'


@dataclass(frozen=True)
class Offer:
    context: tuple
    revision: int
    observed_at: float
    choices: tuple[Choice, ...]


class Matcher:
    def __init__(self, names):
        self.names = {str(k): text(v, 120) for k, v in names.items()
                      if str(k).isascii() and str(k).isdigit() and int(k) > 0
                      and isinstance(v, str) and any(c.isalpha() for c in v)}
        if not self.names or len(self.names) > 4000:
            raise ValueError('Augment catalog unavailable.')
        self.index = {}
        for identifier, name in self.names.items():
            self.index.setdefault(normalized(name), []).append(identifier)

    def match(self, title):
        if not isinstance(title, str) or len(title) > 512:
            return Choice(None, None)
        key = normalized(title)
        ids = self.index.get(key, [])
        if len(ids) == 1:
            return Choice(ids[0], self.names[ids[0]], 'exact')
        # Colliding normalized names and short/ambiguous OCR never guess an ID.
        if ids or len(key) < 8:
            return Choice(None, None)
        scores = sorted(((SequenceMatcher(None, key, candidate).ratio(), values)
                         for candidate, values in self.index.items()
                         if abs(len(candidate) - len(key)) <= 2), reverse=True)
        if (scores and scores[0][0] >= .94 and len(scores[0][1]) == 1
                and (len(scores) == 1 or scores[0][0] - scores[1][0] >= .1)):
            identifier = scores[0][1][0]
            return Choice(identifier, self.names[identifier], 'fuzzy')
        return Choice(None, None)


class OfferState:
    """Two consistent reads confirm; a changed/failed read clears immediately."""
    def __init__(self):
        self._pending = None
        self._offer = None
        self._revision = 0

    def clear(self):
        self._pending = self._offer = None

    def observe(self, context, choices, now):
        if (not math.isfinite(now) or len(choices) != 3
                or sum(c.identifier is not None for c in choices) < 2):
            self.clear()
            return
        ids = [c.identifier for c in choices if c.identifier is not None]
        if len(ids) != len(set(ids)):
            self.clear()
            return
        signature = (context, tuple(c.identifier for c in choices))
        previous = self._pending
        if (previous is None or signature != previous[0]
                or not 0 < now - previous[1] <= 2):
            self._offer = None
        else:
            if self._offer is None:
                self._revision += 1
            self._offer = Offer(context, self._revision, now, tuple(choices))
        self._pending = (signature, now)

    def current(self, context, now):
        if (self._offer is not None and self._offer.context == context
                and 0 <= now - self._offer.observed_at < 2):
            return self._offer
        return None


def offer_view(key, offer, metrics=None, *, mode='arena', source=None):
    """Preserve screen order; metrics are looked up only for the offered IDs."""
    metrics = metrics or {}
    lines = []
    for label, choice in zip(('Esquerda', 'Centro', 'Direita'), offer.choices):
        lines.append(label + ': ' + (choice.name or 'Carta não identificada')
                     + (' (leitura aproximada)' if choice.match == 'fuzzy' else ''))
        row = metrics.get(choice.identifier, {})
        rate, games = row.get('pick_rate'), row.get('games')
        valid_rate = type(rate) in (int, float) and math.isfinite(rate) and 0 <= rate <= 100
        valid_games = type(games) is int and games >= 0
        lines.append(f"PR {rate if valid_rate else '—'}% · {games if valid_games else '—'} jogos")
    lines += ['Popularidade não prevê vitória.',
              source or 'Estatísticas deste modo indisponíveis; sem dados de outro modo.']
    return View(key, (Card(('Arena' if mode == 'arena' else 'ARAM Mayhem') + ' · cartas na tela', tuple(lines)),))
