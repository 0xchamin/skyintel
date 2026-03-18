"""Parse aisstream.io WebSocket messages into NormalizedVessel objects."""

import logging
from datetime import datetime, timezone

from voyageintel.models import NormalizedVessel
from voyageintel.vessels.classifier import classify_vessel_type, detect_military, get_flag_country

logger = logging.getLogger(__name__)

# AIS navigation status codes → human-readable
_NAV_STATUS = {
    0: "underway_engine",
    1: "at_anchor",
    2: "not_under_command",
    3: "restricted_manoeuvrability",
    4: "constrained_by_draught",
    5: "moored",
    6: "aground",
    7: "fishing",
    8: "underway_sailing",
    9: "reserved_hsc",
    10: "reserved_wig",
    11: "power_driven_towing_astern",
    12: "power_driven_pushing",
    14: "ais_sart",
}


def parse_position_report(msg: dict) -> NormalizedVessel | None:
    """Parse AIS message types 1, 2, 3, 18, 19 (position reports)."""
    try:
        meta = msg.get("MetaData", {})
        report = msg.get("Message", {})

        # Unwrap: message is nested under its type key
        if "PositionReport" in report:
            data = report["PositionReport"]
        elif "StandardClassBPositionReport" in report:
            data = report["StandardClassBPositionReport"]
        else:
            return None

        mmsi = str(meta.get("MMSI", "")).strip()
        if not mmsi or len(mmsi) < 5:
            return None

        lat = data.get("Latitude")
        lon = data.get("Longitude")
        if lat is None or lon is None or lat == 91.0 or lon == 181.0:
            return None

        nav_code = data.get("NavigationalStatus")

        return NormalizedVessel(
            mmsi=mmsi,
            name=(meta.get("ShipName") or "").strip() or None,
            latitude=lat,
            longitude=lon,
            cog=data.get("Cog"),
            sog=data.get("Sog"),
            heading=data.get("TrueHeading") if data.get("TrueHeading") != 511 else None,
            rot=data.get("RateOfTurn") if data.get("RateOfTurn") != -128 else None,
            nav_status=_NAV_STATUS.get(nav_code),
            nav_status_code=nav_code,
            flag_country=get_flag_country(mmsi),
            timestamp=meta.get("time_utc") or datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.debug("Failed to parse position report: %s", e)
        return None


def parse_static_data(msg: dict) -> NormalizedVessel | None:
    """Parse AIS message type 5 and 24 (static/voyage data)."""
    try:
        meta = msg.get("MetaData", {})
        report = msg.get("Message", {})

        if "ShipStaticData" in report:
            data = report["ShipStaticData"]
        else:
            return None

        mmsi = str(meta.get("MMSI", "")).strip()
        if not mmsi or len(mmsi) < 5:
            return None

        type_code = data.get("Type")
        vessel_type = classify_vessel_type(type_code)
        name = (data.get("Name") or meta.get("ShipName") or "").strip() or None
        vessel_type = detect_military(name, vessel_type)

        dim = data.get("Dimension", {})
        length = None
        width = None
        if dim:
            a = dim.get("A", 0) or 0
            b = dim.get("B", 0) or 0
            c = dim.get("C", 0) or 0
            d = dim.get("D", 0) or 0
            length = (a + b) if (a + b) > 0 else None
            width = (c + d) if (c + d) > 0 else None

        eta_msg = data.get("Eta", {})
        eta = None
        if eta_msg and eta_msg.get("Month") and eta_msg.get("Day"):
            eta = f"{eta_msg.get('Month'):02d}-{eta_msg.get('Day'):02d} {eta_msg.get('Hour', 0):02d}:{eta_msg.get('Minute', 0):02d}"

        return NormalizedVessel(
            mmsi=mmsi,
            imo=str(data.get("ImoNumber")) if data.get("ImoNumber") else None,
            name=name,
            callsign=(data.get("CallSign") or "").strip() or None,
            vessel_type=vessel_type,
            vessel_type_code=type_code,
            flag_country=get_flag_country(mmsi),
            destination=(data.get("Destination") or "").strip() or None,
            eta=eta,
            draught=data.get("MaximumStaticDraught"),
            length=length,
            width=width,
            timestamp=meta.get("time_utc") or datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.debug("Failed to parse static data: %s", e)
        return None


def parse_message(msg: dict) -> NormalizedVessel | None:
    """Parse any aisstream.io message into a NormalizedVessel."""
    msg_type = msg.get("MessageType")
    if msg_type == "PositionReport":
        return parse_position_report(msg)
    elif msg_type == "StandardClassBPositionReport":
        return parse_position_report(msg)
    elif msg_type == "ShipStaticData":
        return parse_static_data(msg)
    return None
