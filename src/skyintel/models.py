"""Canonical data models for OpenSkyAI."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class NormalizedFlight:
    icao24: str
    callsign: str | None = None
    aircraft_type: str = "commercial"         # commercial / military / private
    model: str | None = None
    operator: str | None = None
    registration: str | None = None
    origin: str | None = None
    destination: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None           # metres
    velocity_ms: float | None = None          # metres/sec
    heading: float | None = None              # degrees true
    vertical_rate: float | None = None        # m/s
    squawk: str | None = None
    source: str = "unknown"                   # opensky / adsb_lol
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
