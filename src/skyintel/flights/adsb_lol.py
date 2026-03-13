import httpx
import logging
import asyncio

from skyintel.models import NormalizedFlight
from skyintel.flights.hubs import HUBS


logger = logging.getLogger(__name__)

ALL_URL = "https://api.adsb.lol/v2/all"
MIL_URL = "https://api.adsb.lol/v2/mil"

# Conversion factors
FT_TO_M = 0.3048
KT_TO_MS = 0.514444
FTMIN_TO_MS = 0.00508


def _normalize(ac: dict, force_military: bool = False) -> NormalizedFlight | None:
    """Convert an ADSB.lol aircraft dict to NormalizedFlight."""
    hex_code = ac.get("hex", "").strip().lower()
    if not hex_code:
        return None

    lat = ac.get("lat")
    lon = ac.get("lon")
    if lat is None or lon is None:
        return None

    # Skip ground traffic
    alt_baro = ac.get("alt_baro")
    if alt_baro == "ground" or alt_baro is None:
        return None

    # Unit conversions: ADSB.lol uses feet, knots, ft/min
    altitude_m = float(alt_baro) * FT_TO_M if isinstance(alt_baro, (int, float)) else None
    gs = ac.get("gs")
    velocity_ms = float(gs) * KT_TO_MS if gs is not None else None
    baro_rate = ac.get("baro_rate")
    vertical_rate = float(baro_rate) * FTMIN_TO_MS if baro_rate is not None else None

    callsign = (ac.get("flight") or "").strip() or None

    return NormalizedFlight(
        icao24=hex_code,
        callsign=callsign,
        aircraft_type="military" if force_military else "commercial",
        model=ac.get("t"),
        registration=ac.get("r"),
        latitude=lat,
        longitude=lon,
        altitude_m=altitude_m,
        velocity_ms=velocity_ms,
        heading=ac.get("track"),
        vertical_rate=vertical_rate,
        squawk=ac.get("squawk"),
        source="adsb_lol",
    )


class AdsbLolClient:
    def __init__(self):
        self._http = httpx.AsyncClient(timeout=30.0)

    async def get_all(self) -> list[NormalizedFlight]:
        """Fetch all worldwide flights."""
        resp = await self._http.get(ALL_URL)
        resp.raise_for_status()
        data = resp.json()

        flights = []
        for ac in data.get("ac", []):
            f = _normalize(ac, force_military=False)
            if f:
                flights.append(f)

        logger.info("ADSB.lol all: %d airborne flights", len(flights))
        return flights

    async def get_military(self) -> list[NormalizedFlight]:
        """Fetch military flights worldwide."""
        resp = await self._http.get(MIL_URL)
        resp.raise_for_status()
        data = resp.json()

        flights = []
        for ac in data.get("ac", []):
            f = _normalize(ac, force_military=True)
            if f:
                flights.append(f)

        logger.info("ADSB.lol military: %d flights", len(flights))
        return flights
    
    async def get_nearby(self, lat: float, lon: float, radius_m: int = 99999) -> list[NormalizedFlight]:
        """Fetch flights within radius of a point (max 99999m)."""
        radius_m = min(radius_m, 99999)
        url = f"https://api.adsb.lol/v2/point/{lat}/{lon}/{radius_m}"
        resp = await self._http.get(url)
        resp.raise_for_status()
        flights = [f for ac in resp.json().get("ac", []) if (f := _normalize(ac))]
        logger.info("ADSB.lol nearby (%.2f,%.2f r=%dm): %d flights", lat, lon, radius_m, len(flights))
        return flights

    async def get_by_callsign(self, callsign: str) -> list[NormalizedFlight]:
        """Fetch flights matching a callsign."""
        url = f"https://api.adsb.lol/v2/callsign/{callsign.strip().upper()}"
        resp = await self._http.get(url)
        resp.raise_for_status()
        flights = [f for ac in resp.json().get("ac", []) if (f := _normalize(ac))]
        logger.info("ADSB.lol callsign %s: %d flights", callsign, len(flights))
        return flights
    
    async def poll_hubs(self) -> list[NormalizedFlight]:
        """Poll all regional hubs in parallel, deduplicate by icao24."""
        from skyintel.flights.hubs import HUBS

        tasks = [self.get_nearby(lat, lon, 99999) for _, _, lat, lon in HUBS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen: dict[str, NormalizedFlight] = {}
        success = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Hub %s poll failed: %s", HUBS[i][0], result)
                continue
            success += 1
            for flight in result:
                if flight.icao24 not in seen:
                    seen[flight.icao24] = flight

        logger.info(
            "Regional poll: %d unique flights from %d/%d hubs",
            len(seen), success, len(HUBS),
        )
        return list(seen.values())


    async def get_by_hex(self, icao24: str) -> list[NormalizedFlight]:
        """Fetch flight by ICAO24 hex code."""
        url = f"https://api.adsb.lol/v2/hex/{icao24.strip().upper()}"
        resp = await self._http.get(url)
        resp.raise_for_status()
        flights = [f for ac in resp.json().get("ac", []) if (f := _normalize(ac))]
        logger.info("ADSB.lol hex %s: %d flights", icao24, len(flights))
        return flights


    async def close(self):
        await self._http.aclose()
