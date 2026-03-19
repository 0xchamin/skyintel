"""Service layer — shared query logic for MCP tools + CLI."""

import logging
import math
from dataclasses import asdict

from voyageintel.config import get_settings
from voyageintel.storage.database import get_db
from voyageintel.flights.adsb_lol import AdsbLolClient
from voyageintel.flights.hexdb import HexdbClient, get_aircraft_cached, get_route_cached
from voyageintel.flights.repository import get_latest_flights
from voyageintel.satellites.repository import get_satellites_by_category, get_satellite_by_norad
from voyageintel.satellites.propagator import propagate_batch, propagate_one
from voyageintel.weather.openmeteo import OpenMeteoClient

from voyageintel.iss.open_notify import OpenNotifyClient
from voyageintel.iss.passes import predict_passes
from voyageintel.satellites.repository import get_satellites_by_category

from voyageintel.vessels.repository import (
    get_vessels_near, get_vessels_by_type, search_vessel, get_vessel_by_mmsi,
    get_military_vessels, get_all_vessels, get_vessel_stats,
)
from voyageintel.ports.repository import get_ports_near, get_port_by_code

from voyageintel.weather.marine import MarineWeatherClient
from voyageintel.geo.geocoder import Geocoder
from voyageintel.geo.resolver import PlaceResolver



# ── Playground runtime stats (updated by server.py poll loops) ──
playground_runtime = {
    "start_time": None,
    "poll_count": 0,
    "last_flight_poll": None,
    "last_sat_poll": None,
    "flights_commercial": 0,
    "flights_military": 0,
    "flights_private": 0,
    "source_health": {
        "adsb_lol":   {"healthy": False, "last_success": None, "error": None},
        "celestrak":  {"healthy": False, "last_success": None, "error": None},
        "hexdb":      {"healthy": True,  "last_success": None, "error": None},
        "open_meteo": {"healthy": True,  "last_success": None, "error": None},
        "aisstream": {"healthy": False, "last_success": None, "error": None},
    },
    "vessels_total": 0,
    "ais_connected": False,
    "ais_messages": 0,
    "ais_flushes": 0,
}

logger = logging.getLogger(__name__)
# _settings = get_settings()
# _adsb = AdsbLolClient()
# _hexdb = HexdbClient()
# _weather = OpenMeteoClient()
# _marine_weather = MarineWeatherClient()
# _geocoder = Geocoder(api_key=_settings.google_maps_api_key)
# _resolver = PlaceResolver(_geocoder)
# _open_notify = OpenNotifyClient()
_settings = get_settings()
_adsb = AdsbLolClient()
_hexdb = HexdbClient()
_weather = OpenMeteoClient()
_marine_weather = MarineWeatherClient()
_geocoder = Geocoder(api_key=_settings.google_maps_api_key)
_resolver = PlaceResolver(_geocoder)
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
    from voyageintel.satellites.propagator import propagate_one
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
    from voyageintel.server import _poll_count, _last_poll_total, _last_poll_military, _satellite_count
    return {
        "status": "ok",
        "flight_poll_count": _poll_count,
        "last_poll_total": _last_poll_total,
        "last_poll_military": _last_poll_military,
        "satellites_cached": _satellite_count,
    }

async def get_playground_system() -> dict:
    """System metrics for playground dashboard."""
    import os, time

    settings = get_settings()
    db = await get_db(settings.db_path)

    rt = playground_runtime
    flights_commercial = rt["flights_commercial"]
    flights_military = rt["flights_military"]
    flights_private = rt["flights_private"]

    sat_row = await db.execute("SELECT COUNT(*) as total, COUNT(DISTINCT category) as cats FROM satellites")
    sat_counts = await sat_row.fetchone()

    db_size = None
    try:
        db_size = os.path.getsize(settings.db_path)
    except OSError:
        pass

    uptime = time.time() - rt["start_time"] if rt["start_time"] else None

    return {
        "flights_commercial": flights_commercial,
        "flights_military": flights_military,
        "flights_private": flights_private,
        "satellites_cached": sat_counts["total"] if sat_counts else 0,
        "satellite_categories": sat_counts["cats"] if sat_counts else 0,
        "poll_count": rt["poll_count"],
        "uptime_seconds": round(uptime, 1) if uptime else None,
        "last_flight_poll": rt["last_flight_poll"],
        "last_sat_poll": rt["last_sat_poll"],
        "flight_poll_interval": settings.flight_poll_interval,
        "satellite_poll_interval": settings.satellite_poll_interval,
        "db_size_bytes": db_size,
        "db_path": str(settings.db_path),
        "sources": rt["source_health"],
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_api_key_set": bool(settings.llm_api_key),
        "langfuse_configured": bool(settings.langfuse_public_key and settings.langfuse_secret_key),
    }


async def get_playground_guardrails() -> dict:
    """Guardrail stats for playground dashboard."""
    try:
        from voyageintel.llm.guardrails import get_guardrail_stats
        stats = get_guardrail_stats()
        return {**stats, "available": True}
    except ImportError:
        return {
            "available": False,
            "input_scans": 0,
            "output_scans": 0,
            "blocked_count": 0,
            "blocked_by_scanner": {},
            "scanners": [],
            "recent_blocks": [],
        }

async def get_playground_langfuse() -> dict:
    """LangFuse analytics for playground dashboard."""
    import json
    import httpx
    from base64 import b64encode
    from datetime import datetime, timezone, timedelta
    from voyageintel.llm.gateway import get_tool_call_counts as _get_tool_call_counts


    settings = get_settings()

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return {"available": False, "reason": "LangFuse keys not configured"}

    host = settings.langfuse_host.rstrip("/")
    auth_str = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}"
    auth_header = f"Basic {b64encode(auth_str.encode()).decode()}"
    headers = {"Authorization": auth_header}

    now = datetime.now(timezone.utc)
    from_ts = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    result = {
        "available": True,
        "host": host,
        "total_traces": 0,
        "avg_latency_ms": None,
        "total_tokens": {"input": 0, "output": 0, "total": 0},
        "cost_by_model": {},
        "tool_calls": {},
        "tool_calls": _get_tool_call_counts(),

        "error_count": 0,
        "daily_metrics": [],
    }

    async with httpx.AsyncClient(timeout=15.0) as client:

        # ── 1. Total traces (v1 traces API returns meta.totalItems) ──
        try:
            resp = await client.get(
                f"{host}/api/public/traces",
                params={"limit": 1},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                result["total_traces"] = data.get("meta", {}).get("totalItems", 0)
        except Exception as e:
            logger.warning("LangFuse traces fetch failed: %s", e)

        # ── 2. Average latency (v2 metrics — observations view) ──
        try:
            query = json.dumps({
                "view": "observations",
                "metrics": [{"measure": "latency", "aggregation": "avg"}],
                "dimensions": [],
                "filters": [],
                "fromTimestamp": from_ts,
                "toTimestamp": to_ts,
            })
            resp = await client.get(
                f"{host}/api/public/v2/metrics",
                params={"query": query},
                headers=headers,
            )
            if resp.status_code == 200:
                rows = resp.json().get("data", [])
                if rows:
                    val = rows[0].get("latency_avg")
                    if val is not None:
                        result["avg_latency_ms"] = round(float(val), 1)
        except Exception as e:
            logger.warning("LangFuse latency fetch failed: %s", e)

        # ── 3. Total tokens (v2 metrics) ──
        try:
            query = json.dumps({
                "view": "observations",
                "metrics": [
                    {"measure": "inputTokens", "aggregation": "sum"},
                    {"measure": "outputTokens", "aggregation": "sum"},
                    {"measure": "totalTokens", "aggregation": "sum"},
                ],
                "dimensions": [],
                "filters": [],
                "fromTimestamp": from_ts,
                "toTimestamp": to_ts,
            })
            resp = await client.get(
                f"{host}/api/public/v2/metrics",
                params={"query": query},
                headers=headers,
            )
            if resp.status_code == 200:
                rows = resp.json().get("data", [])
                if rows:
                    row = rows[0]
                    result["total_tokens"] = {
                        "input": int(row.get("inputTokens_sum", 0) or 0),
                        "output": int(row.get("outputTokens_sum", 0) or 0),
                        "total": int(row.get("totalTokens_sum", 0) or 0),
                    }
        except Exception as e:
            logger.warning("LangFuse tokens fetch failed: %s", e)

        # ── 4. Cost by model (v2 metrics) ──
        try:
            query = json.dumps({
                "view": "observations",
                "metrics": [{"measure": "totalCost", "aggregation": "sum"}],
                "dimensions": [{"field": "providedModelName"}],
                "filters": [],
                "fromTimestamp": from_ts,
                "toTimestamp": to_ts,
                "orderBy": [{"field": "totalCost_sum", "direction": "desc"}],
            })
            resp = await client.get(
                f"{host}/api/public/v2/metrics",
                params={"query": query},
                headers=headers,
            )
            if resp.status_code == 200:
                cost_by_model = {}
                for row in resp.json().get("data", []):
                    model = row.get("providedModelName", "unknown")
                    cost = float(row.get("totalCost_sum", 0) or 0)
                    if model and cost > 0:
                        cost_by_model[model] = round(cost, 6)
                result["cost_by_model"] = cost_by_model
        except Exception as e:
            logger.warning("LangFuse cost fetch failed: %s", e)

        # ── 5. Tool call frequency (v2 metrics — count by observation name) ──
                # ── 5. Tool call frequency (from in-memory gateway tracking) ──
        try:
            from voyageintel.llm.gateway import get_tool_call_counts
            result["tool_calls"] = get_tool_call_counts()
        except ImportError:
            pass

        # try:
        #     query = json.dumps({
        #         "view": "observations",
        #         "metrics": [{"measure": "count", "aggregation": "count"}],
        #         "dimensions": [{"field": "name"}],
        #         "filters": [],
        #         "fromTimestamp": from_ts,
        #         "toTimestamp": to_ts,
        #         "orderBy": [{"field": "count_count", "direction": "desc"}],
        #     })
        #     resp = await client.get(
        #         f"{host}/api/public/v2/metrics",
        #         params={"query": query},
        #         headers=headers,
        #     )
        #     if resp.status_code == 200:
        #         tool_calls = {}
        #         for row in resp.json().get("data", []):
        #             name = row.get("name", "unknown")
        #             count = int(row.get("count_count", 0) or 0)
        #             if name and count > 0:
        #                 tool_calls[name] = count
        #         result["tool_calls"] = tool_calls
        # except Exception as e:
        #     logger.warning("LangFuse tool calls fetch failed: %s", e)

        # ── 6. Daily metrics (v1 daily endpoint) ──
        try:
            resp = await client.get(
                f"{host}/api/public/metrics/daily",
                params={"limit": 30},
                headers=headers,
            )
            if resp.status_code == 200:
                result["daily_metrics"] = resp.json().get("data", [])[:30]
        except Exception as e:
            logger.warning("LangFuse daily metrics fetch failed: %s", e)

    return result

# ── Vessel queries ───────────────────────────────────────────

async def vessels_near(lat: float, lon: float, radius_km: float = 50, max_results: int = 50) -> dict:
    """Get live vessels near a point."""
    db = await get_db(_settings.db_path)
    results = await get_vessels_near(db, lat, lon, radius_km, max_results)
    return {"results": results, "total_count": len(results)}


async def vessel_search(query: str, max_results: int = 50) -> dict:
    """Search for a vessel by name, MMSI, or IMO."""
    db = await get_db(_settings.db_path)
    results = await search_vessel(db, query, max_results)
    return {"results": results, "total_count": len(results)}


async def military_vessels_list(max_results: int = 50) -> dict:
    """Get all tracked military/naval vessels."""
    db = await get_db(_settings.db_path)
    results = await get_military_vessels(db, max_results)
    return {"results": results, "total_count": len(results)}


async def vessels_by_type(vessel_type: str, max_results: int = 50) -> dict:
    """Get vessels filtered by type."""
    db = await get_db(_settings.db_path)
    results = await get_vessels_by_type(db, vessel_type, max_results)
    return {"results": results, "total_count": len(results)}


async def vessel_info(mmsi: str) -> dict | None:
    """Get vessel detail by MMSI."""
    db = await get_db(_settings.db_path)
    return await get_vessel_by_mmsi(db, mmsi)


async def vessel_stats() -> dict:
    """Get vessel count by type."""
    db = await get_db(_settings.db_path)
    return await get_vessel_stats(db)


# ── Port queries ─────────────────────────────────────────────

async def ports_near(lat: float, lon: float, radius_km: float = 50, max_results: int = 20) -> dict:
    """Find ports near a location."""
    db = await get_db(_settings.db_path)
    results = await get_ports_near(db, lat, lon, radius_km, max_results)
    return {"results": results, "total_count": len(results)}


async def port_info(code: str) -> dict | None:
    """Get port details by UN/LOCODE."""
    db = await get_db(_settings.db_path)
    return await get_port_by_code(db, code)

# ── Marine weather ───────────────────────────────────────────

async def sea_weather(lat: float, lon: float) -> dict | None:
    """Get marine weather at a location."""
    return await _marine_weather.get_current(lat, lon)


# ── Geocoding ────────────────────────────────────────────────

async def geocode(place_name: str) -> dict | None:
    """Resolve a place name to coordinates."""
    db = await get_db(_settings.db_path)
    return await _geocoder.geocode(place_name, db)


# ── Vessel destination/origin queries ────────────────────────

async def vessels_to(destination: str, max_results: int = 50) -> dict:
    """Find vessels heading to a destination (searches AIS destination field)."""
    db = await get_db(_settings.db_path)
    q = destination.strip().upper()
    async with db.execute(
        """
        SELECT * FROM vessels
        WHERE UPPER(destination) LIKE ?
        ORDER BY vessel_type = 'military' DESC, updated_at DESC
        LIMIT ?
        """,
        (f"%{q}%", max_results),
    ) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
    return {"results": results, "total_count": len(results)}


async def vessels_from(port_code: str, radius_km: float = 25, max_results: int = 50) -> dict:
    """Find vessels near/departing a port by UN/LOCODE."""
    db = await get_db(_settings.db_path)
    port = await get_port_by_code(db, port_code)
    if not port:
        return {"results": [], "total_count": 0, "error": f"Port {port_code} not found"}
    results = await get_vessels_near(db, port["latitude"], port["longitude"], radius_km, max_results)
    return {"results": results, "total_count": len(results), "port": port}


# ── Cross-domain queries ────────────────────────────────────

async def activity_near(lat: float, lon: float, radius_km: float = 100, max_results: int = 50) -> dict:
    """All activity near a point — flights + vessels."""
    flights_data = await flights_near(lat, lon, radius_km, max_results)
    vessels_data = await vessels_near(lat, lon, radius_km, max_results)
    return {
        "flights": flights_data,
        "vessels": vessels_data,
    }


async def military_activity(lat: float, lon: float, radius_km: float = 200, max_results: int = 50) -> dict:
    """Military assets near a point — aircraft + naval vessels."""
    flights_data = await flights_near(lat, lon, radius_km, max_results)
    mil_flights = [f for f in flights_data.get("results", []) if f.get("aircraft_type") == "military"]

    vessels_data = await vessels_near(lat, lon, radius_km, max_results)
    mil_vessels = [v for v in vessels_data.get("results", []) if v.get("vessel_type") == "military"]

    return {
        "military_aircraft": {"results": mil_flights, "total_count": len(mil_flights)},
        "military_vessels": {"results": mil_vessels, "total_count": len(mil_vessels)},
    }

async def cleanup():
    """Close all HTTP clients."""
    await _adsb.close()
    await _hexdb.close()
    await _weather.close()
    await _open_notify.close()
