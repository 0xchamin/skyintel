import asyncio
import logging
from pathlib import Path
from dataclasses import asdict
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from skyintel.config import get_settings
from skyintel.flights.opensky import OpenSkyClient
from skyintel.flights.adsb_lol import AdsbLolClient
from skyintel.flights.merge import merge_flights
from skyintel.flights.repository import insert_flights, get_latest_flights, prune_old_flights
from skyintel.satellites.celestrak import CelestrakClient
from skyintel.satellites.propagator import propagate_batch
from skyintel.satellites.repository import upsert_satellites, get_satellites_by_category
from skyintel.storage.database import get_db, close_db

from skyintel.weather.openmeteo import OpenMeteoClient


logger = logging.getLogger(__name__)

settings = get_settings()
WEB_DIR = Path(__file__).parent / "ui" / "web"

opensky = OpenSkyClient(
    client_id=settings.opensky_client_id,
    client_secret=settings.opensky_client_secret,
)
adsb = AdsbLolClient()
celestrak = CelestrakClient()
weather = OpenMeteoClient()


_poll_count = 0
_last_poll_total = 0
_last_poll_military = 0
_satellite_count = 0


# ── Flight Poller ────────────────────────────────────────────
async def flight_poll_loop():
    global _poll_count, _last_poll_total, _last_poll_military
    await asyncio.sleep(2)
    logger.info("Flight poller started (interval=%ds)", settings.flight_poll_interval)

    while True:
        try:
            db = await get_db(settings.db_path)
            adsb_all, opensky_all, adsb_mil = await asyncio.gather(
                adsb.get_all(),
                opensky.get_states(),
                adsb.get_military(),
                return_exceptions=True,
            )
            if isinstance(adsb_all, Exception):
                logger.error("ADSB.lol all failed: %s", adsb_all)
                adsb_all = []
            if isinstance(opensky_all, Exception):
                logger.error("OpenSky failed: %s", opensky_all)
                opensky_all = []
            if isinstance(adsb_mil, Exception):
                logger.error("ADSB.lol mil failed: %s", adsb_mil)
                adsb_mil = []

            merged = merge_flights(adsb_all, opensky_all, adsb_mil)
            await insert_flights(db, merged)

            _poll_count += 1
            _last_poll_total = len(merged)
            _last_poll_military = sum(1 for f in merged if f.aircraft_type == "military")

            if _poll_count % 10 == 0:
                await prune_old_flights(db)

            logger.info("Flight poll #%d: %d flights (%d military)", _poll_count, _last_poll_total, _last_poll_military)
        except Exception:
            logger.exception("Flight poll failed")

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
        except Exception:
            logger.exception("Satellite poll failed")

        await asyncio.sleep(settings.satellite_poll_interval)


# ── Routes ───────────────────────────────────────────────────
async def index(request):
    return FileResponse(WEB_DIR / "index.html")


async def api_status(request):
    return JSONResponse({
        "status": "ok",
        "opensky_auth": opensky.authenticated,
        "flight_poll_count": _poll_count,
        "last_poll_total": _last_poll_total,
        "last_poll_military": _last_poll_military,
        "satellites_cached": _satellite_count,
        "port": settings.port,
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


async def api_satellites(request):
    """Return current satellite positions, optionally filtered by category."""
    db = await get_db(settings.db_path)
    category = request.query_params.get("category")
    tles = await get_satellites_by_category(db, category)

    if not tles:
        return JSONResponse([])

    positions = propagate_batch(tles)
    return JSONResponse(positions)


# ── Lifecycle ────────────────────────────────────────────────
async def on_startup():
    logger.info("OpenSkyAI starting on %s:%d", settings.host, settings.port)
    from skyintel.storage.migrations import run_migrations
    db = await get_db(settings.db_path)
    await run_migrations(db)

    asyncio.create_task(flight_poll_loop())
    asyncio.create_task(satellite_poll_loop())


async def on_shutdown():
    await opensky.close()
    await adsb.close()
    await celestrak.close()
    await weather.close()
    await close_db()
    logger.info("OpenSkyAI stopped")


# ── App ──────────────────────────────────────────────────────
app = Starlette(
    routes=[
        Route("/", index),
        Route("/api/status", api_status),
        Route("/api/flights", api_flights),
        Route("/api/satellites", api_satellites),
        Route("/api/weather", api_weather),
    ],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
