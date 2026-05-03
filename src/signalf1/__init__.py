"""SignalF1 — F1 SignalR telemetry ingestion."""

__version__ = "0.1.0"

__all__ = ["SignalF1", "LiveTimingData"]

from ._client import SignalRClient as SignalF1
from ._data import LiveTimingData as LiveTimingData
