"""Merge flights from ADSB.lol (primary) + OpenSky (supplementary)."""

import logging
from osai.models import NormalizedFlight
from osai.flights.classifier import classify

logger = logging.getLogger(__name__)


def merge_flights(
    adsb_flights: list[NormalizedFlight],
    opensky_flights: list[NormalizedFlight],
    mil_flights: list[NormalizedFlight],
) -> list[NormalizedFlight]:
    """
    Merge strategy:
      1. ADSB.lol /v2/all is the primary source (unfiltered positions)
      2. OpenSky supplements with metadata where available
      3. ADSB.lol /v2/mil tags additional military aircraft
      4. Classifier catches anything else via callsign/hex/squawk
    """
    # Index by icao24
    merged: dict[str, NormalizedFlight] = {}

    # Layer 1: ADSB.lol all (primary)
    for f in adsb_flights:
        merged[f.icao24] = f

    # Layer 2: OpenSky fills in metadata gaps
    for f in opensky_flights:
        if f.icao24 in merged:
            existing = merged[f.icao24]
            # Fill any None fields from OpenSky
            if existing.callsign is None and f.callsign:
                existing.callsign = f.callsign
            if existing.squawk is None and f.squawk:
                existing.squawk = f.squawk
        else:
            # OpenSky has aircraft not in ADSB.lol — add it
            merged[f.icao24] = f

    # Layer 3: Military overlay tags
    mil_icao24s = {f.icao24 for f in mil_flights}
    for icao24 in mil_icao24s:
        if icao24 in merged:
            merged[icao24].aircraft_type = "military"

    # Layer 4: Run classifier on everything
    for f in merged.values():
        f.aircraft_type = classify(f)

    result = list(merged.values())
    mil_count = sum(1 for f in result if f.aircraft_type == "military")
    logger.info("Merged: %d total flights (%d military)", len(result), mil_count)
    return result
