"""Errors exposed by the independent LoLalytics collector."""


class CollectorError(Exception):
    """A collection failed; callers must not turn this into an empty success."""


class QueryError(CollectorError, ValueError):
    pass


class TransportError(CollectorError):
    pass


class HTTPStatusError(TransportError):
    def __init__(self, status: int, retry_after: float | None = None):
        self.status = status
        self.retry_after = retry_after
        super().__init__(f"LoLalytics returned HTTP {status}")


class ResponseTooLarge(TransportError):
    pass


class SchemaError(CollectorError):
    pass


class DataUnavailable(CollectorError):
    pass
