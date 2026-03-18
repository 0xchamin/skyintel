"""ISS pass predictions using Skyfield."""

import logging
import math
from datetime import datetime, timezone, timedelta
from skyfield.api import EarthSatellite, load, wgs84

logger = logging.getLogger(__name__)

_ts = load.timescale()

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _az_to_compass(deg: float) -> str:
    return COMPASS[round(deg / 22.5) % 16]


def predict_passes(
    tle_line1: str,
    tle_line2: str,
    lat: float,
    lon: float,
    hours: int = 24,
    min_elevation: float = 10.0,
) -> list[dict]:
    """Predict ISS passes over a ground location.

    Args:
        tle_line1: TLE line 1 for ISS
        tle_line2: TLE line 2 for ISS
        lat: Observer latitude
        lon: Observer longitude
        hours: Lookahead window in hours (default 24)
        min_elevation: Minimum peak elevation in degrees (default 10)

    Returns:
        List of pass dicts with rise/culmination/set times, azimuths, and max elevation.
    """
    try:
        sat = EarthSatellite(tle_line1, tle_line2, "ISS (ZARYA)", _ts)
        observer = wgs84.latlon(lat, lon)

        t0 = _ts.from_datetime(datetime.now(timezone.utc))
        t1 = _ts.from_datetime(datetime.now(timezone.utc) + timedelta(hours=hours))

        times, events = sat.find_events(observer, t0, t1, altitude_degrees=0.0)

        passes = []
        current_pass = {}

        for t, event in zip(times, events):
            dt = t.utc_datetime()
            difference = sat - observer
            topocentric = difference.at(t)
            alt, az, distance = topocentric.altaz()

            if event == 0:  # rise
                current_pass = {
                    "rise_utc": dt.isoformat(),
                    "rise_azimuth": round(float(az.degrees), 1),
                    "rise_direction": _az_to_compass(float(az.degrees)),
                }
            elif event == 1:  # culmination
                current_pass["max_elevation"] = round(float(alt.degrees), 1)
                current_pass["max_elevation_utc"] = dt.isoformat()
                current_pass["max_azimuth"] = round(float(az.degrees), 1)
                current_pass["max_direction"] = _az_to_compass(float(az.degrees))
            elif event == 2:  # set
                current_pass["set_utc"] = dt.isoformat()
                current_pass["set_azimuth"] = round(float(az.degrees), 1)
                current_pass["set_direction"] = _az_to_compass(float(az.degrees))
                current_pass["duration_seconds"] = round(
                    (dt - datetime.fromisoformat(current_pass["rise_utc"])).total_seconds()
                )

                if current_pass.get("max_elevation", 0) >= min_elevation:
                    passes.append(current_pass)
                current_pass = {}

        logger.info("ISS passes for (%.2f, %.2f): %d passes in next %dh", lat, lon, len(passes), hours)
        return passes

    except Exception as e:
        logger.error("ISS pass prediction failed: %s", e)
        return []
