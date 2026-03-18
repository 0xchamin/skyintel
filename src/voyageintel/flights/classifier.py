"""Classify aircraft as military / commercial / private."""

import re

# Military callsign prefixes (common worldwide)
MILITARY_CALLSIGN_PREFIXES = {
    "RCH", "REACH", "DUKE", "NAVY", "EVAC", "COBRA", "VIPER",
    "HAWK", "EAGLE", "RAPTOR", "BOXER", "DOOM", "SKULL", "IRON",
    "FURY", "BLADE", "GHOST", "REAPER", "WEASEL", "KNIGHT",
    "RAID", "TOPCAT", "STEEL", "TANGO", "WOLF", "TALON",
    "HAVOC", "ROGUE", "STORM", "MAGMA", "ATLAS", "DRAKE",
    "NATO", "ASCOT", "RAFALE", "CASA", "SHARK", "SIGINT",
    "RRR", "CFC", "CNV", "PLF", "FAB", "IAM", "MMF",
}

# ICAO hex ranges allocated to military (partial list, major countries)
MILITARY_HEX_RANGES = [
    ("ae0000", "afffff"),  # US military
    ("43c000", "43cfff"),  # UK military
    ("3f0000", "3fffff"),  # Germany military
    ("3a8000", "3abfff"),  # France military
    ("300000", "33ffff"),  # Italy military (partial)
]

PRIVATE_JET_TYPES = {
    # Gulfstream
    "GLF2", "GLF3", "GLF4", "GLF5", "GLF6", "GALX", "G150", "G200", "G280", "GL7T",
    # Bombardier
    "CL30", "CL35", "CL60", "GL5T", "GLEX", "BD70",
    # Cessna Citation
    "C500", "C510", "C525", "C550", "C560", "C56X", "C650", "C680", "C700", "C750",
    # Dassault Falcon
    "FA50", "FA7X", "FA8X", "F900", "F2TH",
    # Embraer
    "E35L", "E50P", "E55P", "E545",
    # Learjet
    "LJ35", "LJ40", "LJ45", "LJ60", "LJ75",
    # Hawker / Beechcraft
    "H25B", "HA4T", "BE40", "PRM1",
    # Pilatus
    "PC12", "PC24",
}


# Squawk codes associated with military
MILITARY_SQUAWKS = {"7501", "7502", "7503", "7504", "7505", "0021", "0022", "0023"}

_compiled_prefixes = re.compile(
    r"^(" + "|".join(re.escape(p) for p in MILITARY_CALLSIGN_PREFIXES) + r")",
    re.IGNORECASE,
)


def _hex_in_military_range(icao24: str) -> bool:
    try:
        val = int(icao24, 16)
    except (ValueError, TypeError):
        return False
    for lo, hi in MILITARY_HEX_RANGES:
        if int(lo, 16) <= val <= int(hi, 16):
            return True
    return False


def classify(flight) -> str:
    """
    Classify a NormalizedFlight. Returns 'military', 'commercial', or 'private'.
    If already tagged as military (e.g. from ADSB.lol /v2/mil), preserves that.
    """
    # Already tagged military by source
    if flight.aircraft_type == "military":
        return "military"

    # Callsign match
    if flight.callsign and _compiled_prefixes.match(flight.callsign):
        return "military"

    # ICAO hex range
    if _hex_in_military_range(flight.icao24):
        return "military"

    # Squawk code
    if flight.squawk and flight.squawk in MILITARY_SQUAWKS:
        return "military"
    
    if flight.model and flight.model.upper() in PRIVATE_JET_TYPES:
        return "private"


    return flight.aircraft_type
