"""Service layer — shared query logic for MCP tools + CLI."""

import logging
import math
from dataclasses import asdict

from skyintel.config import get_settings
from skyintel.storage.database import get_db
from skyintel.flights.adsb_lol import AdsbLolClient
from skyintel.flights.hexdb import HexdbClient, get_aircraft_cached, get_route_cached
from skyintel.flights.repository import get_latest_flights
from skyintel.satellites.repository import get_satellites_by_category, get_satellite_by_norad
from skyintel.satellites.propagator import propagate_batch, propagate_one
from skyintel.weather.openmeteo import OpenMeteoClient

logger = logging.getLogger(__name__)

_adsb = AdsbLolClient()
_hexdb = HexdbClient()
_weather = OpenMeteoClient()
_settings = get_settings()


async def flights_near(lat: float, lon: float, radius_km: float = 100) -> list[dict]:
    """Get live flights near a point via ADSB.lol on-demand."""
    radius_m = min(int(radius_km * 1000), 99999)
    flights = await _adsb.get_nearby(lat, lon, radius_m)
    return [asdict(f) for f in flights]


async def search_flight(query: str) -> list[dict]:
    """Search for a flight by callsign or ICAO24 hex."""
    query = query.strip().upper()
    # Hex codes are 6 chars, all hex digits
    if len(query) == 6 and all(c in "0123456789ABCDEF" for c in query):
        flights = await _adsb.get_by_hex(query)
    else:
        flights = await _adsb.get_by_callsign(query)
    return [asdict(f) for f in flights]


async def military_flights() -> list[dict]:
    """Get all current military flights."""
    flights = await _adsb.get_military()
    return [asdict(f) for f in flights]


async def flights_to(destination_icao: str) -> list[dict]:
    """Find cached flights heading to a destination airport."""
    db = await get_db(_settings.db_path)
    async with db.execute(
        "SELECT r.callsign, r.origin_icao, r.destination_icao "
        "FROM routes r WHERE r.destination_icao = ?",
        (destination_icao.strip().upper(),),
    ) as cursor:
        rows = await cursor.fetchall()
    if not rows:
        return []
    callsigns = [r[0] for r in rows]
    flights = await get_latest_flights(db)
    return [f for f in flights if f.get("callsign", "").strip().upper() in callsigns]


async def flights_from(origin_icao: str) -> list[dict]:
    """Find cached flights departed from an origin airport."""
    db = await get_db(_settings.db_path)
    async with db.execute(
        "SELECT r.callsign, r.origin_icao, r.destination_icao "
        "FROM routes r WHERE r.origin_icao = ?",
        (origin_icao.strip().upper(),),
    ) as cursor:
        rows = await cursor.fetchall()
    if not rows:
        return []
    callsigns = [r[0] for r in rows]
    flights = await get_latest_flights(db)
    return [f for f in flights if f.get("callsign", "").strip().upper() in callsigns]


async def aircraft_info(icao24: str) -> dict | None:
    """Get enriched aircraft metadata."""
    db = await get_db(_settings.db_path)
    return await get_aircraft_cached(db, _hexdb, icao24)


async def get_satellites(category: str | None = None) -> list[dict]:
    """Get current satellite positions."""
    db = await get_db(_settings.db_path)
    tles = await get_satellites_by_category(db, category)
    if not tles:
        return []
    return propagate_batch(tles)


# async def get_satellite(norad_id: int) -> dict | None:
#     """Get a single satellite position by NORAD ID."""
#     db = await get_db(_settings.db_path)
#     tle = await get_satellite_by_norad(db, norad_id)
#     if not tle:
#         return None
#     return propagate_one(tle["name"], tle["tle_line1"], tle["tle_line2"], tle["norad_id"], tle["category"])

async def get_satellites(category: str | None = None) -> list[dict]:
    """Get current satellite positions."""
    if category and category.lower() in ("null", "none", ""):
        category = None
    db = await get_db(_settings.db_path)
    tles = await get_satellites_by_category(db, category)
    if not tles:
        return []
    return propagate_batch(tles)



async def get_weather(lat: float, lon: float) -> dict | None:
    """Get current weather at a location."""
    return await _weather.get_current(lat, lon)


async def get_status() -> dict:
    """Get system status."""
    from skyintel.server import _poll_count, _last_poll_total, _last_poll_military, _satellite_count
    return {
        "status": "ok",
        "flight_poll_count": _poll_count,
        "last_poll_total": _last_poll_total,
        "last_poll_military": _last_poll_military,
        "satellites_cached": _satellite_count,
    }
