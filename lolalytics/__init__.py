"""Unofficial, standalone LoLalytics collector for SEXO2 phase one."""
from .client import Client
from .builds import BuildCollection, BuildPage, ItemBlock, ItemChoice
from .item_pages import PreparedItemBlock, PreparedItemPage, plan_item_pages
from .matchups import build_matchup_page
from .errors import (CollectorError, DataUnavailable, HTTPStatusError, QueryError,
                     ResponseTooLarge, SchemaError, TransportError)
from .models import Record, Snapshot
from .query import Query
from .recommendations import Recommendation

__all__ = ["Client", "Query", "Record", "Snapshot", "BuildCollection", "BuildPage",
           "ItemBlock", "ItemChoice", "CollectorError", "QueryError",
           "PreparedItemBlock", "PreparedItemPage", "plan_item_pages", "build_matchup_page",
           "TransportError", "HTTPStatusError", "ResponseTooLarge", "SchemaError", "DataUnavailable"]
__all__.append("Recommendation")
