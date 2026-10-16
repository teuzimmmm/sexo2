"""Conservative, explicit queries for the HTTP-confirmed page routes."""
from dataclasses import asdict, dataclass
import re
from urllib.parse import urlencode

from .errors import QueryError

MODES = ("ranked", "aram", "arena")
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

    def __post_init__(self):
        if not isinstance(self.champion, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", self.champion):
            raise QueryError("champion must be an explicit lowercase LoLalytics slug, e.g. ahri")
        for name, values in (("mode", MODES), ("lane", LANES), ("tier", TIERS), ("region", REGIONS)):
            if getattr(self, name) not in values:
                raise QueryError(f"unsupported {name}; accepted values: {', '.join(values)}")
        if self.mode != "ranked" and self.lane != "all":
            raise QueryError("lane is only supported for ranked")
        if self.mode != "ranked" and (self.tier not in ("emerald_plus", "all") or self.region != "all"):
            raise QueryError("ARAM/Arena currently support only tier emerald_plus/all and region all")
        if self.patch is not None and (not isinstance(self.patch, str) or not re.fullmatch(r"\d{2}\.\d{1,2}", self.patch)):
            raise QueryError("patch must have the observed format, e.g. 16.20")

    @property
    def url(self) -> str:
        mode = "" if self.mode == "ranked" else f"{self.mode}/"
        # ARAM rejects even lane=all with HTTP 404. Modes have separate query
        # contracts although their resolved navigation still reports lane=all.
        params = ({"lane": self.lane} if self.mode == "ranked" else {})
        params.update({"tier": self.tier, "region": self.region})
        if self.patch is not None:
            params["patch"] = self.patch
        return f"https://lolalytics.com/lol/{self.champion}/{mode}build/q-data.json?{urlencode(params)}"

    @property
    def key(self) -> str:
        return self.url

    def to_dict(self) -> dict:
        return asdict(self)
