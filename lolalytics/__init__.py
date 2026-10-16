"""Unofficial, standalone LoLalytics collector for SEXO2 phase one."""
from .client import Client
from .errors import (CollectorError, DataUnavailable, HTTPStatusError, QueryError,
                     ResponseTooLarge, SchemaError, TransportError)
from .models import Record, Snapshot
from .query import Query

__all__ = ["Client", "Query", "Record", "Snapshot", "CollectorError", "QueryError",
           "TransportError", "HTTPStatusError", "ResponseTooLarge", "SchemaError", "DataUnavailable"]
