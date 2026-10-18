"""Conservative, explicit queries for the HTTP-confirmed page routes."""

from dataclasses import asdict, dataclass
import re
from urllib.parse import urlencode

from .errors import QueryError

MODES = ("ranked", "aram", "arena", "swift")
LANES = ("all", "top", "jungle", "middle", "bottom", "support")
# Deliberately narrow until more values have concrete HTTP evidence.
TIERS = ("emerald_plus", "diamond_plus", "gold", "all")
REGIONS = ("all", "br")


@dataclass(frozen=True)
class Query:
    champion: str
    mode: str = "ranked"
    patch: str | None = None
    lane: str = "all"
    tier: str = "emerald_plus"
    region: str = "all"
    keystone: int | None = None
    opponent: str | None = None
    opponent_lane: str = "all"

    def __post_init__(self):
        if not isinstance(self.champion, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", self.champion):
            raise QueryError("champion must be an explicit lowercase LoLalytics slug, e.g. ahri")
        for name, values in (("mode", MODES), ("lane", LANES), ("tier", TIERS), ("region", REGIONS)):
            if getattr(self, name) not in values:
                raise QueryError(f"unsupported {name}; accepted values: {', '.join(values)}")
        if self.opponent is not None and (
            not isinstance(self.opponent, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", self.opponent)
        ):
            raise QueryError("opponent must be an explicit lowercase LoLalytics slug")
        if self.opponent_lane not in LANES:
            raise QueryError(f"unsupported opponent_lane; accepted values: {', '.join(LANES)}")
        if self.opponent is None and self.opponent_lane != "all":
            raise QueryError("opponent_lane requires an opponent")
        if self.opponent is not None:
            if self.mode != "ranked":
                raise QueryError("opponent is only supported for ranked")
            if self.region != "all":
                raise QueryError("opponent queries currently support only region all")
            if self.keystone is not None:
                raise QueryError("keystone filtering is not supported with an opponent")
        if self.mode != "ranked" and self.lane != "all":
            raise QueryError("lane is only supported for ranked")
        if self.keystone is not None:
            if isinstance(self.keystone, bool) or not isinstance(self.keystone, int) or self.keystone <= 0:
                raise QueryError("keystone must be a positive integer")
            if self.mode not in ("ranked", "aram"):
                raise QueryError("keystone is only supported for ranked and ARAM")
        if self.mode != "ranked" and (self.tier not in ("emerald_plus", "all") or self.region != "all"):
            raise QueryError("non-ranked modes currently support only tier emerald_plus/all and region all")
        if self.mode == "swift" and self.tier != "emerald_plus":
            raise QueryError("Swiftplay currently supports only tier emerald_plus")
        if self.patch is not None and (
            not isinstance(self.patch, str) or not re.fullmatch(r"\d{2}\.\d{1,2}", self.patch)
        ):
            raise QueryError("patch must have the observed format, e.g. 16.20")

    @property
    def url(self) -> str:
        if self.opponent is not None:
            params = {"lane": self.lane, "vslane": self.opponent_lane, "tier": self.tier}
            if self.patch is not None:
                params["patch"] = self.patch
            return (
                f"https://lolalytics.com/lol/{self.champion}/vs/{self.opponent}/build/q-data.json?{urlencode(params)}"
            )
        mode = "" if self.mode == "ranked" else f"{self.mode}/"
        # ARAM rejects even lane=all with HTTP 404. Modes have separate query
        # contracts although their resolved navigation still reports lane=all.
        params = {"lane": self.lane} if self.mode == "ranked" else {}
        params.update({"tier": self.tier, "region": self.region})
        if self.patch is not None:
            params["patch"] = self.patch
        if self.keystone is not None:
            params["keystone"] = self.keystone
        return f"https://lolalytics.com/lol/{self.champion}/{mode}build/q-data.json?{urlencode(params)}"

    @property
    def key(self) -> str:
        return self.url

    def to_dict(self) -> dict:
        return asdict(self)
