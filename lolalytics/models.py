"""Serializable domain records, independent of the SEXO2 runtime."""
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Record:
    category: str
    identifiers: list[str]
    metrics: dict[str, int | float | None]
    source_path: str
    raw: Any
    metric_scope: str


@dataclass
class Snapshot:
    query: dict
    resolved: dict
    source_url: str
    collected_at: str
    overview: dict
    records: list[Record]
    raw: dict
    availability: dict[str, str]
    warnings: list[str] = field(default_factory=list)
    stale: bool = False
    cache_hit: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)
