"""Satellite position propagation using Skyfield + sgp4."""

import logging
import math
from datetime import datetime, timezone
from skyfield.api import EarthSatellite, load

logger = logging.getLogger(__name__)

_ts = load.timescale()


def propagate_one(name: str, tle_line1: str, tle_line2: str, norad_id: int,
                  category: str, at_time: datetime | None = None) -> dict | None:
    """Propagate a single satellite to get its current position."""
    try:
        sat = EarthSatellite(tle_line1, tle_line2, name, _ts)
        t = _ts.from_datetime(at_time or datetime.now(timezone.utc))

        geocentric = sat.at(t)
        subpoint = geocentric.subpoint()

        # Velocity as magnitude of 3-vector (km/s → m/s)
        vel = geocentric.velocity.km_per_s
        speed_ms = math.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2) * 1000

        if not all(math.isfinite(v) for v in (subpoint.latitude.degrees, subpoint.longitude.degrees, subpoint.elevation.km, speed_ms)):
            return None

        return {
            "norad_id": norad_id,
            "name": name,
            "category": category,
            "latitude": float(subpoint.latitude.degrees),
            "longitude": float(subpoint.longitude.degrees),
            "altitude_km": float(subpoint.elevation.km),
            "speed_ms": round(speed_ms, 1),
            "inclination": round(float(tle_line2[8:16].strip()), 2),
        }
    except Exception as e:
        logger.debug("Propagation failed for %s (%d): %s", name, norad_id, e)
        return None


def propagate_batch(satellites: list[dict], at_time: datetime | None = None) -> list[dict]:
    """Propagate a batch of satellites. Returns list of position dicts."""
    results = []
    for sat in satellites:
        pos = propagate_one(
            name=sat["name"],
            tle_line1=sat["tle_line1"],
            tle_line2=sat["tle_line2"],
            norad_id=sat["norad_id"],
            category=sat["category"],
            at_time=at_time,
        )
        if pos:
            results.append(pos)

    logger.info("Propagated %d / %d satellites", len(results), len(satellites))
    return results
