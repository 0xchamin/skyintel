"""Merge flights from ADSB.lol regional polls + military."""

import logging
from voyageintel.models import NormalizedFlight
from voyageintel.flights.classifier import classify

logger = logging.getLogger(__name__)


def merge_flights(
    adsb_flights: list[NormalizedFlight],
    mil_flights: list[NormalizedFlight],
) -> list[NormalizedFlight]:
    """
    Merge strategy:
      1. ADSB.lol regional polls are the primary source
      2. ADSB.lol /v2/mil tags additional military aircraft
      3. Classifier catches anything else via callsign/hex/squawk
    """
    merged: dict[str, NormalizedFlight] = {}

    # Layer 1: Regional ADSB.lol (primary)
    for f in adsb_flights:
        merged[f.icao24] = f

    # Layer 2: Military overlay + add mil-only flights
    for f in mil_flights:
        if f.icao24 in merged:
            merged[f.icao24].aircraft_type = "military"
        else:
            f.aircraft_type = "military"
            merged[f.icao24] = f

    # Layer 3: Classify anything the sources missed
    for f in merged.values():
        f.aircraft_type = classify(f)

    result = list(merged.values())
    mil_count = sum(1 for f in result if f.aircraft_type == "military")
    logger.info("Merged: %d total flights (%d military)", len(result), mil_count)
    return result
