import asyncio
import logging
import time
import os
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse, HTMLResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
import contextlib

from skyintel.config import get_settings
from skyintel.flights.adsb_lol import AdsbLolClient
from skyintel.flights.merge import merge_flights
from skyintel.flights.repository import insert_flights, get_latest_flights, prune_old_flights
from skyintel.satellites.celestrak import CelestrakClient
from skyintel.satellites.propagator import propagate_batch
from skyintel.satellites.repository import upsert_satellites, get_satellites_by_category
from skyintel.storage.database import get_db, close_db
from skyintel.flights.hexdb import HexdbClient, get_aircraft_cached, get_route_cached
from skyintel.mcp_tools import mcp
from skyintel.llm.gateway import chat as llm_chat
from skyintel.weather.openmeteo import OpenMeteoClient
from skyintel.service import playground_runtime
from skyintel import service



logger = logging.getLogger(__name__)

settings = get_settings()
WEB_DIR = Path(__file__).parent / "ui" / "web"

adsb = AdsbLolClient()
celestrak = CelestrakClient()
weather = OpenMeteoClient()
hexdb = HexdbClient()

_poll_count = 0
_last_poll_total = 0
_last_poll_military = 0
_satellite_count = 0


# ── Flight Poller (Regional ADSB.lol) ───────────────────────
async def flight_poll_loop():
    global _poll_count, _last_poll_total, _last_poll_military
    await asyncio.sleep(2)
    logger.info("Regional flight poller started (interval=%ds)", settings.flight_poll_interval)

    while True:
        try:
            db = await get_db(settings.db_path)

            regional, adsb_mil = await asyncio.gather(
                adsb.poll_hubs(),
                adsb.get_military(),
                return_exceptions=True,
            )

            if isinstance(regional, Exception):
                logger.error("Regional poll failed: %s", regional)
                regional = []
            if isinstance(adsb_mil, Exception):
                logger.error("ADSB.lol mil failed: %s", adsb_mil)
                adsb_mil = []

            merged = merge_flights(regional, adsb_mil)
            await insert_flights(db, merged)

            playground_runtime["flights_commercial"] = sum(1 for f in merged if f.aircraft_type == "commercial")
            playground_runtime["flights_military"] = sum(1 for f in merged if f.aircraft_type == "military")
            playground_runtime["flights_private"] = sum(1 for f in merged if f.aircraft_type == "private")


            _poll_count += 1
            _last_poll_total = len(merged)
            _last_poll_military = sum(1 for f in merged if f.aircraft_type == "military")

            if _poll_count % 10 == 0:
                await prune_old_flights(db)

            logger.info(
                "Flight poll #%d: %d flights (%d military)",
                _poll_count, _last_poll_total, _last_poll_military,
            )

              
            logger.info("DEBUG playground_runtime flights: c=%d m=%d p=%d",
                playground_runtime["flights_commercial"],
                playground_runtime["flights_military"],
                playground_runtime["flights_private"])

            playground_runtime["poll_count"] = _poll_count
            playground_runtime["last_flight_poll"] = datetime.now(timezone.utc).isoformat()
            playground_runtime["source_health"]["adsb_lol"]["healthy"] = True
            playground_runtime["source_health"]["adsb_lol"]["last_success"] = playground_runtime["last_flight_poll"]
            playground_runtime["source_health"]["adsb_lol"]["error"] = None

        except Exception as e:
            logger.exception("Flight poll failed")
            playground_runtime["source_health"]["adsb_lol"]["healthy"] = False
            playground_runtime["source_health"]["adsb_lol"]["error"] = str(e)

        await asyncio.sleep(settings.flight_poll_interval)


# ── Satellite Poller ─────────────────────────────────────────
async def satellite_poll_loop():
    global _satellite_count
    await asyncio.sleep(5)
    logger.info("Satellite poller started (interval=%ds)", settings.satellite_poll_interval)

    while True:
        try:
            db = await get_db(settings.db_path)
            sats = await celestrak.fetch_all()
            await upsert_satellites(db, sats)
            _satellite_count = len(sats)
            logger.info("Satellite poll: %d TLEs cached", _satellite_count)

            playground_runtime["last_sat_poll"] = datetime.now(timezone.utc).isoformat()
            playground_runtime["source_health"]["celestrak"]["healthy"] = True
            playground_runtime["source_health"]["celestrak"]["last_success"] = playground_runtime["last_sat_poll"]
            playground_runtime["source_health"]["celestrak"]["error"] = None

        except Exception as e:
            logger.exception("Satellite poll failed")
            playground_runtime["source_health"]["celestrak"]["healthy"] = False
            playground_runtime["source_health"]["celestrak"]["error"] = str(e)

        await asyncio.sleep(settings.satellite_poll_interval)


# ── Routes ───────────────────────────────────────────────────
async def index(request):
    html = (WEB_DIR / "index.html").read_text()
    token = settings.cesium_ion_token or ""
    html = html.replace("%%CESIUM_TOKEN%%", token)
    return HTMLResponse(html)


async def api_status(request):
    return JSONResponse({
        "status": "ok",
        "flight_poll_count": _poll_count,
        "last_poll_total": _last_poll_total,
        "last_poll_military": _last_poll_military,
        "satellites_cached": _satellite_count,
        "port": settings.port,
        "cesium_configured": settings.cesium_ion_token is not None,
    })


async def api_weather(request):
    """Get current weather at a lat/lon."""
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")
    if lat is None or lon is None:
        return JSONResponse({"error": "lat and lon required"}, status_code=400)
    data = await weather.get_current(float(lat), float(lon))
    if data is None:
        return JSONResponse({"error": "weather fetch failed"}, status_code=502)
    return JSONResponse(data)


async def api_chat(request):
    """Chat endpoint — proxies to LLM with tool calling."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    messages = body.get("messages")
    provider = body.get("provider")
    api_key = body.get("api_key")
    model = body.get("model")

    if not messages or not provider or not api_key or not model:
        return JSONResponse({"error": "messages, provider, api_key, and model are required"}, status_code=400)

    try:
        reply = await llm_chat(messages, provider, api_key, model)
        return JSONResponse({"reply": reply})
    except Exception as e:
        logger.error("Chat failed: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)

async def api_chat_stream(request):
    """Streaming chat endpoint — SSE."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    messages = body.get("messages")
    provider = body.get("provider")
    api_key = body.get("api_key")
    model = body.get("model")

    if not messages or not provider or not api_key or not model:
        return JSONResponse({"error": "messages, provider, api_key, and model are required"}, status_code=400)

    from skyintel.llm.gateway import chat_stream
    from starlette.responses import StreamingResponse

    return StreamingResponse(
        chat_stream(messages, provider, api_key, model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

async def api_flights(request):
    db = await get_db(settings.db_path)
    lat_min = float(request.query_params.get("lat_min", -90))
    lat_max = float(request.query_params.get("lat_max", 90))
    lon_min = float(request.query_params.get("lon_min", -180))
    lon_max = float(request.query_params.get("lon_max", 180))
    flights = await get_latest_flights(db, lat_min, lat_max, lon_min, lon_max)
    for f in flights:
        f.pop("latest", None)
    return JSONResponse(flights)


async def api_aircraft(request):
    """Get aircraft metadata by ICAO24 hex code."""
    icao24 = request.path_params["icao24"]
    db = await get_db(settings.db_path)
    data = await get_aircraft_cached(db, hexdb, icao24)
    if not data:
        return JSONResponse({"error": "Aircraft not found"}, status_code=404)
    return JSONResponse(data)


async def api_route(request):
    """Get flight route by callsign."""
    callsign = request.path_params["callsign"]
    db = await get_db(settings.db_path)
    data = await get_route_cached(db, hexdb, callsign)
    if not data:
        return JSONResponse({"error": "Route not found"}, status_code=404)
    return JSONResponse(data)


async def api_satellites(request):
    """Return current satellite positions, optionally filtered by category."""
    db = await get_db(settings.db_path)
    category = request.query_params.get("category")
    tles = await get_satellites_by_category(db, category)

    if not tles:
        return JSONResponse([])

    positions = propagate_batch(tles)
    return JSONResponse(positions)


# ── ISS ────────────────────────────────────────────────
async def api_iss(request):
    """Get current ISS position + crew."""
    from skyintel import service
    position = await service.iss_position()
    crew = await service.iss_crew()
    return JSONResponse({"position": position, "crew": crew})


async def api_iss_passes(request):
    """Get ISS pass predictions for a location."""
    from skyintel import service
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")
    if lat is None or lon is None:
        return JSONResponse({"error": "lat and lon required"}, status_code=400)
    hours = int(request.query_params.get("hours", 24))
    result = await service.iss_passes(float(lat), float(lon), hours)
    return JSONResponse(result)


# ── Playground ───────────────────────────────────────────────
async def playground_page(request):
    settings = get_settings()
    if not settings.playground_enabled:
        return JSONResponse({"error": "Playground disabled"}, status_code=403)
    html_path = Path(__file__).parent / "ui" / "playground" / "playground.html"
    return HTMLResponse(html_path.read_text())


# async def playground_system(request):
#     settings = get_settings()
#     if not settings.playground_enabled:
#         return JSONResponse({"error": "Playground disabled"}, status_code=403)
#     db = await get_db(settings.db_path)

#     # Flight counts by type
#     row = await db.execute(
#         """SELECT
#             COUNT(*) as total,
#             SUM(CASE WHEN aircraft_type='commercial' THEN 1 ELSE 0 END) as commercial,
#             SUM(CASE WHEN aircraft_type='military' THEN 1 ELSE 0 END) as military,
#             SUM(CASE WHEN aircraft_type='private' THEN 1 ELSE 0 END) as private
#         FROM flights
#         WHERE timestamp > datetime('now', '-2 minutes')"""
#     )
#     counts = await row.fetchone()

#     # Satellite count + categories
#     sat_row = await db.execute("SELECT COUNT(*) as total, COUNT(DISTINCT category) as cats FROM satellites")
#     sat_counts = await sat_row.fetchone()

#     # DB file size
#     db_size = None
#     try:
#         db_size = os.path.getsize(settings.db_path)
#     except OSError:
#         pass

#     uptime = time.time() - playground_runtime["start_time"] if playground_runtime["start_time"] else None

#     return JSONResponse({
#         "flights_commercial": counts["commercial"] if counts else 0,
#         "flights_military": counts["military"] if counts else 0,
#         "flights_private": counts["private"] if counts else 0,
#         "satellites_cached": sat_counts["total"] if sat_counts else 0,
#         "satellite_categories": sat_counts["cats"] if sat_counts else 0,
#         "poll_count": playground_runtime["poll_count"],
#         "uptime_seconds": round(uptime, 1) if uptime else None,
#         "last_flight_poll": playground_runtime["source_health"]["adsb_lol"]["last_success"],
#         "last_sat_poll": playground_runtime["source_health"]["celestrak"]["last_success"],
#         "flight_poll_interval": settings.flight_poll_interval,
#         "satellite_poll_interval": settings.satellite_poll_interval,
#         "db_size_bytes": db_size,
#         "db_path": str(settings.db_path),
#         "sources": playground_runtime["source_health"],
#         "llm_provider": settings.llm_provider,
#         "llm_model": settings.llm_model,
#         "llm_api_key_set": bool(settings.llm_api_key),
#         "langfuse_configured": bool(settings.langfuse_public_key and settings.langfuse_secret_key),
#     })


# async def playground_guardrails(request):
#     settings = get_settings()
#     if not settings.playground_enabled:
#         return JSONResponse({"error": "Playground disabled"}, status_code=403)
#     try:
#         from skyintel.llm.guardrails import get_guardrail_stats
#         stats = get_guardrail_stats()
#         return JSONResponse({**stats, "available": True})
#     except ImportError:
#         return JSONResponse({
#             "available": False,
#             "input_scans": 0,
#             "output_scans": 0,
#             "blocked_count": 0,
#             "blocked_by_scanner": {},
#             "scanners": [],
#             "recent_blocks": [],
#         })

async def playground_system(request):
    settings = get_settings()
    if not settings.playground_enabled:
        return JSONResponse({"error": "Playground disabled"}, status_code=403)
    return JSONResponse(await service.get_playground_system())


async def playground_guardrails(request):
    settings = get_settings()
    if not settings.playground_enabled:
        return JSONResponse({"error": "Playground disabled"}, status_code=403)
    return JSONResponse(await service.get_playground_guardrails())

async def playground_langfuse(request):
    settings = get_settings()
    if not settings.playground_enabled:
        return JSONResponse({"error": "Playground disabled"}, status_code=403)
    return JSONResponse(await service.get_playground_langfuse())

# ── Lifecycle ────────────────────────────────────────────────
async def on_startup():
    logger.info("Open Sky Intelligence starting on %s:%d", settings.host, settings.port)
    from skyintel.storage.migrations import run_migrations
    db = await get_db(settings.db_path)
    await run_migrations(db)

    asyncio.create_task(flight_poll_loop())
    asyncio.create_task(satellite_poll_loop())


async def on_shutdown():
    await adsb.close()
    await celestrak.close()
    await weather.close()
    await close_db()
    logger.info("Open Sky Intelligence stopped")


mcp_app = mcp.http_app(path="/")


# ── App ──────────────────────────────────────────────────────
@contextlib.asynccontextmanager
async def lifespan(app):
    playground_runtime["start_time"] = time.time()
    await on_startup()
    async with mcp_app.router.lifespan_context(app):
        yield
    await on_shutdown()


app = Starlette(
    routes=[
        Route("/", index),
        Route("/api/status", api_status),
        Route("/api/flights", api_flights),
        Route("/api/aircraft/{icao24}", api_aircraft),
        Route("/api/route/{callsign}", api_route),
        Route("/api/satellites", api_satellites),
        Route("/api/weather", api_weather),
        Mount("/mcp", app=mcp_app),
        Route("/api/chat", api_chat, methods=["POST"]),
        Route("/api/chat/stream", api_chat_stream, methods=["POST"]),
        Route("/api/iss", api_iss),
        Route("/api/iss/passes", api_iss_passes),
        Route("/playground", endpoint=playground_page),
        Route("/api/playground/system", endpoint=playground_system),
        Route("/api/playground/guardrails", endpoint=playground_guardrails),
        Route("/api/playground/langfuse", endpoint=playground_langfuse),

    ],
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.mount("/playground", StaticFiles(directory=str(Path(__file__).parent / "ui" / "playground")), name="playground_static")
