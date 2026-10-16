"""Application adapter for LoLalytics recommendations and saved risk choice."""
from lolalytics.risk import validate_risk_level

from .settings import get_risk_level


class LolalyticsService:
    """Apply the app preference to an injected standalone collector client."""

    def __init__(self, client):
        self.client = client

    def recommend(self, query, *, risk_level=None):
        level = get_risk_level() if risk_level is None else validate_risk_level(risk_level)
        return self.client.recommend(query, risk_level=level)
