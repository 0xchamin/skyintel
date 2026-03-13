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

from skyintel.iss.open_notify import OpenNotifyClient
from skyintel.iss.passes import predict_passes
from skyintel.satellites.repository import get_satellites_by_category


logger = logging.getLogger(__name__)

_adsb = AdsbLolClient()
_hexdb = HexdbClient()
_weather = OpenMeteoClient()
_settings = get_settings()
_open_notify = OpenNotifyClient()



async def flights_near(lat: float, lon: float, radius_km: float = 100, max_results: int = 50) -> dict:
    """Get live flights near a point via ADSB.lol on-demand."""
    radius_m = min(int(radius_km * 1000), 99999)
    flights = await _adsb.get_nearby(lat, lon, radius_m)
    results = [asdict(f) for f in flights]
    results.sort(key=lambda f: (f["aircraft_type"] != "military", -(f.get("altitude_m") or 0)))
    return {"results": results[:max_results], "total_count": len(results)}

async def search_flight(query: str, max_results: int = 50) -> dict:
    """Search for a flight by callsign or ICAO24 hex."""
    query = query.strip().upper()
    if len(query) == 6 and all(c in "0123456789ABCDEF" for c in query):
        flights = await _adsb.get_by_hex(query)
    else:
        flights = await _adsb.get_by_callsign(query)
    results = [asdict(f) for f in flights]
    return {"results": results[:max_results], "total_count": len(results)}


async def military_flights(max_results: int = 50) -> dict:
    """Get all current military flights."""
    flights = await _adsb.get_military()
    results = [asdict(f) for f in flights]
    results.sort(key=lambda f: -(f.get("altitude_m") or 0))
    return {"results": results[:max_results], "total_count": len(results)}

async def flights_to(destination_icao: str, max_results: int = 50) -> dict:
    """Find cached flights heading to a destination airport."""
    db = await get_db(_settings.db_path)
    async with db.execute(
        "SELECT r.callsign, r.origin_icao, r.destination_icao "
        "FROM routes r WHERE r.destination_icao = ?",
        (destination_icao.strip().upper(),),
    ) as cursor:
        rows = await cursor.fetchall()
    if not rows:
        return {"results": [], "total_count": 0}
    callsigns = [r[0] for r in rows]
    flights = await get_latest_flights(db)
    results = [f for f in flights if f.get("callsign", "").strip().upper() in callsigns]
    return {"results": results[:max_results], "total_count": len(results)}

async def flights_from(origin_icao: str, max_results: int = 50) -> dict:
    """Find cached flights departed from an origin airport."""
    db = await get_db(_settings.db_path)
    async with db.execute(
        "SELECT r.callsign, r.origin_icao, r.destination_icao "
        "FROM routes r WHERE r.origin_icao = ?",
        (origin_icao.strip().upper(),),
    ) as cursor:
        rows = await cursor.fetchall()
    if not rows:
        return {"results": [], "total_count": 0}
    callsigns = [r[0] for r in rows]
    flights = await get_latest_flights(db)
    results = [f for f in flights if f.get("callsign", "").strip().upper() in callsigns]
    return {"results": results[:max_results], "total_count": len(results)}


async def aircraft_info(icao24: str) -> dict | None:
    """Get enriched aircraft metadata."""
    db = await get_db(_settings.db_path)
    try:
        return await get_aircraft_cached(db, _hexdb, icao24)
    except Exception as e:
        logger.warning("aircraft_info failed for %s: %s", icao24, e)
        return {"error": "Aircraft database temporarily unavailable", "icao24": icao24}


async def get_satellites(category: str | None = None, max_results: int = 50) -> dict:
    """Get current satellite positions."""
    if category and category.lower() in ("null", "none", ""):
        category = None
    db = await get_db(_settings.db_path)
    tles = await get_satellites_by_category(db, category)
    if not tles:
        return {"results": [], "total_count": 0}
    results = propagate_batch(tles)
    results.sort(key=lambda s: -(s.get("altitude_km") or 0))
    return {"results": results[:max_results], "total_count": len(results)}


async def iss_position() -> dict:
    """Get current ISS position using SGP4 propagation."""
    db = await get_db(_settings.db_path)
    tles = await get_satellites_by_category(db, "iss")
    iss_tle = next((t for t in tles if "ZARYA" in t["name"].upper()), None)
    if not iss_tle:
        return {"error": "ISS TLE not found — satellite poller may not have run yet"}
    from skyintel.satellites.propagator import propagate_one
    pos = propagate_one(iss_tle["name"], iss_tle["tle_line1"], iss_tle["tle_line2"], iss_tle["norad_id"], "iss")
    if not pos:
        return {"error": "ISS propagation failed"}
    return pos


async def iss_crew() -> dict:
    """Get current ISS crew."""
    crew = await _open_notify.get_crew()
    return {"crew": crew, "count": len(crew)}


async def iss_passes(lat: float, lon: float, hours: int = 24, min_elevation: float = 10.0) -> dict:
    """Predict ISS passes over a location."""
    db = await get_db(_settings.db_path)
    tles = await get_satellites_by_category(db, "iss")
    iss_tle = next((t for t in tles if "ZARYA" in t["name"].upper()), None)
    if not iss_tle:
        return {"error": "ISS TLE not found — satellite poller may not have run yet"}
    passes = predict_passes(iss_tle["tle_line1"], iss_tle["tle_line2"], lat, lon, hours, min_elevation)
    return {"passes": passes, "total_count": len(passes), "location": {"lat": lat, "lon": lon}}


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

async def cleanup():
    """Close all HTTP clients."""
    await _adsb.close()
    await _hexdb.close()
    await _weather.close()
    await _open_notify.close()
