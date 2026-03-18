"""Canonical data models for VoyageIntel."""

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


@dataclass
class NormalizedVessel:
    mmsi: str                                  # Maritime Mobile Service Identity (9 digits)
    imo: str | None = None                     # IMO number (7 digits)
    name: str | None = None
    callsign: str | None = None
    vessel_type: str = "unknown"               # cargo/tanker/passenger/military/fishing/recreational/special/high_speed/unknown
    vessel_type_code: int | None = None        # AIS ship type code (0-99)
    flag_country: str | None = None            # Flag state (derived from MMSI MID)
    latitude: float | None = None
    longitude: float | None = None
    cog: float | None = None                   # Course over ground (degrees)
    sog: float | None = None                   # Speed over ground (knots)
    heading: float | None = None               # True heading (degrees)
    rot: float | None = None                   # Rate of turn (degrees/min)
    nav_status: str | None = None              # underway/at_anchor/moored/aground/fishing
    nav_status_code: int | None = None         # AIS nav status code (0-15)
    destination: str | None = None
    eta: str | None = None
    draught: float | None = None               # metres
    length: float | None = None                # metres
    width: float | None = None                 # metres
    source: str = "aisstream"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Port:
    code: str                                  # UN/LOCODE (e.g. USLAX, GBSOU, SGSIN)
    name: str
    country: str
    latitude: float
    longitude: float
    port_type: str | None = None               # seaport / river_port / offshore
    size: str | None = None                    # large / medium / small
