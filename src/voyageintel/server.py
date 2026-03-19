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

from voyageintel.config import get_settings
from voyageintel.flights.adsb_lol import AdsbLolClient
from voyageintel.flights.merge import merge_flights
from voyageintel.flights.repository import insert_flights, get_latest_flights, prune_old_flights
from voyageintel.satellites.celestrak import CelestrakClient
from voyageintel.satellites.propagator import propagate_batch
from voyageintel.satellites.repository import upsert_satellites, get_satellites_by_category
from voyageintel.storage.database import get_db, close_db
from voyageintel.flights.hexdb import HexdbClient, get_aircraft_cached, get_route_cached
from voyageintel.mcp_tools import mcp
from voyageintel.llm.gateway import chat as llm_chat
from voyageintel.weather.openmeteo import OpenMeteoClient
from voyageintel.service import playground_runtime
from voyageintel import service
from voyageintel.vessels.aisstream import AisStreamClient
from voyageintel.vessels.repository import prune_stale_vessels, get_vessel_stats
from voyageintel.ports.repository import load_ports


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

# AIS client — initialised in lifespan if API key is set
_ais_client: AisStreamClient | None = None


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


# ── Vessel Prune Task ────────────────────────────────────────
async def vessel_prune_loop():
    """Prune stale vessels every 10 minutes."""
    await asyncio.sleep(60)  # initial delay
    logger.info("Vessel prune task started (retention=%dh)", settings.vessel_prune_hours)

    while True:
        try:
            db = await get_db(settings.db_path)
            await prune_stale_vessels(db, settings.vessel_prune_hours)
        except Exception:
            logger.exception("Vessel prune failed")
        await asyncio.sleep(600)  # every 10 minutes


# ── AIS Stats Updater ────────────────────────────────────────
async def ais_stats_loop():
    """Update playground runtime stats from AIS client every 10 seconds."""
    await asyncio.sleep(10)

    while True:
        try:
            if _ais_client:
                stats = _ais_client.stats
                playground_runtime["ais_connected"] = stats["connected"]
                playground_runtime["ais_messages"] = stats["messages_received"]
                playground_runtime["ais_flushes"] = stats["flushes"]
                playground_runtime["source_health"]["aisstream"]["healthy"] = stats["connected"]
                if stats["connected"]:
                    playground_runtime["source_health"]["aisstream"]["last_success"] = datetime.now(timezone.utc).isoformat()
                    playground_runtime["source_health"]["aisstream"]["error"] = None

                # Update vessel counts
                db = await get_db(settings.db_path)
                vstats = await get_vessel_stats(db)
                playground_runtime["vessels_total"] = vstats.get("total", 0)
        except Exception:
            logger.debug("AIS stats update failed", exc_info=True)
        await asyncio.sleep(10)


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
        "vessels_tracked": playground_runtime.get("vessels_total", 0),
        "ais_connected": playground_runtime.get("ais_connected", False),
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

async def api_sea_weather(request):
    """Get marine weather at a lat/lon."""
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")
    if lat is None or lon is None:
        return JSONResponse({"error": "lat and lon required"}, status_code=400)
    from voyageintel.weather.marine import MarineWeatherClient
    client = MarineWeatherClient()
    data = await client.get_current(float(lat), float(lon))
    await client.close()
    if data is None:
        return JSONResponse({"error": "marine weather fetch failed"}, status_code=502)
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

    from voyageintel.llm.gateway import chat_stream
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
    from voyageintel import service
    position = await service.iss_position()
    crew = await service.iss_crew()
    return JSONResponse({"position": position, "crew": crew})


async def api_iss_passes(request):
    """Get ISS pass predictions for a location."""
    from voyageintel import service
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")
    if lat is None or lon is None:
        return JSONResponse({"error": "lat and lon required"}, status_code=400)
    hours = int(request.query_params.get("hours", 24))
    result = await service.iss_passes(float(lat), float(lon), hours)
    return JSONResponse(result)


# ── Vessel Endpoints ─────────────────────────────────────────
async def api_vessels(request):
    """Get vessels in bounding box."""
    from voyageintel.vessels.repository import get_all_vessels
    db = await get_db(settings.db_path)
    lat_min = float(request.query_params.get("lat_min", -90))
    lat_max = float(request.query_params.get("lat_max", 90))
    lon_min = float(request.query_params.get("lon_min", -180))
    lon_max = float(request.query_params.get("lon_max", 180))
    vessels = await get_all_vessels(db, lat_min, lat_max, lon_min, lon_max)
    return JSONResponse(vessels)


async def api_vessel_detail(request):
    """Get vessel detail by MMSI."""
    mmsi = request.path_params["mmsi"]
    result = await service.vessel_info(mmsi)
    if not result:
        return JSONResponse({"error": "Vessel not found"}, status_code=404)
    return JSONResponse(result)


async def api_vessel_stats(request):
    """Get vessel count by type."""
    result = await service.vessel_stats()
    return JSONResponse(result)


# ── Port Endpoints ───────────────────────────────────────────
async def api_ports(request):
    """Get ports near a location."""
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")
    if lat is None or lon is None:
        return JSONResponse({"error": "lat and lon required"}, status_code=400)
    radius_km = float(request.query_params.get("radius_km", 50))
    result = await service.ports_near(float(lat), float(lon), radius_km)
    return JSONResponse(result)


async def api_port_detail(request):
    """Get port detail by UN/LOCODE."""
    code = request.path_params["code"]
    result = await service.port_info(code)
    if not result:
        return JSONResponse({"error": "Port not found"}, status_code=404)
    return JSONResponse(result)


# ── Playground ───────────────────────────────────────────────
async def playground_page(request):
    settings = get_settings()
    if not settings.playground_enabled:
        return JSONResponse({"error": "Playground disabled"}, status_code=403)
    html_path = Path(__file__).parent / "ui" / "playground" / "playground.html"
    return HTMLResponse(html_path.read_text())


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
    global _ais_client
    logger.info("VoyageIntel starting on %s:%d", settings.host, settings.port)
    from voyageintel.storage.migrations import run_migrations
    db = await get_db(settings.db_path)
    await run_migrations(db)

    # Load ports
    await load_ports(db)

    # Start flight + satellite pollers
    asyncio.create_task(flight_poll_loop())
    asyncio.create_task(satellite_poll_loop())

    # Start AIS WebSocket client if API key is set
    if settings.aisstream_api_key:
        _ais_client = AisStreamClient(settings.aisstream_api_key, db)
        await _ais_client.start()
        asyncio.create_task(vessel_prune_loop())
        asyncio.create_task(ais_stats_loop())
        logger.info("AIS stream enabled — maritime tracking active")
    else:
        logger.info("AIS stream disabled — no VI_AISSTREAM_API_KEY set")


async def on_shutdown():
    global _ais_client
    if _ais_client:
        await _ais_client.stop()
        _ais_client = None
    await adsb.close()
    await celestrak.close()
    await weather.close()
    await close_db()
    logger.info("VoyageIntel stopped")


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
        Route("/api/sea-weather", api_sea_weather),
        Mount("/mcp", app=mcp_app),
        Route("/api/chat", api_chat, methods=["POST"]),
        Route("/api/chat/stream", api_chat_stream, methods=["POST"]),
        Route("/api/iss", api_iss),
        Route("/api/iss/passes", api_iss_passes),
        # Vessels
        Route("/api/vessels", api_vessels),
        Route("/api/vessel/{mmsi}", api_vessel_detail),
        Route("/api/vessels/stats", api_vessel_stats),
        # Ports
        Route("/api/ports", api_ports),
        Route("/api/port/{code}", api_port_detail),
        # Playground
        Route("/playground", endpoint=playground_page),
        Route("/api/playground/system", endpoint=playground_system),
        Route("/api/playground/guardrails", endpoint=playground_guardrails),
        Route("/api/playground/langfuse", endpoint=playground_langfuse),
    ],
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.mount("/playground", StaticFiles(directory=str(Path(__file__).parent / "ui" / "playground")), name="playground_static")
