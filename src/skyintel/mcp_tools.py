"""MCP tools for Open Sky Intelligence — streamable HTTP + stdio."""

from fastmcp import FastMCP

from skyintel import service

mcp = FastMCP(
    name="Open Sky Intelligence",
    instructions="""You are an expert aviation and space intelligence analyst with access to real-time data through Open Sky Intelligence tools.

## Your Capabilities
- Live flight tracking worldwide (commercial, military, private)
- Unfiltered military aircraft monitoring (a key differentiator — most commercial trackers hide these)
- Satellite position tracking across 6 categories (ISS, military, weather, navigation, science, Starlink)
- Aircraft metadata enrichment (manufacturer, type, owner, registration)
- Flight route lookup (origin/destination airports)
- Real-time weather at any location

## Tool Selection Guidelines
- **flights_near**: Use when the user asks about flights over/above/near a location. You know world geography — convert place names to lat/lon coordinates yourself.
- **search_flight**: Use when the user mentions a specific callsign (e.g. 'RYR123'), ICAO24 hex code, or registration.
- **military_flights**: Use for any query about military, government, or defense-related air activity.
- **flights_to / flights_from**: Use when the user asks about flights heading to or departing from a specific airport. Convert airport names to ICAO codes yourself (e.g. Amsterdam Schiphol = EHAM, London Heathrow = EGLL).
- **aircraft_info**: Use to enrich any flight with detailed aircraft metadata. Always call this when generating reports or when the user asks about a specific aircraft's specs.
- **get_satellites**: Use for satellite queries. Pass a category filter when the user specifies one.
- **get_weather**: Use to provide atmospheric context for any location. Always include weather when generating comprehensive reports.
- **get_status**: Use only when asked about system health or diagnostics.

## Report Generation
When asked to generate a report (HTML, summary, briefing, etc.):
1. Gather data by calling multiple tools in sequence — flights, aircraft metadata, satellites, and weather as relevant.
2. Synthesise the data into a well-structured, visually rich HTML5 document.
3. Use semantic HTML with inline CSS for styling (dark theme, modern typography).
4. Include tables for tabular data, summary statistics, and contextual narrative.
5. Add section headers, timestamps (UTC), and source attribution.
6. For aircraft, enrich with metadata from aircraft_info where possible.

## Response Style
- Use aviation terminology accurately (FL350 = Flight Level 350 = ~35,000ft, kt = knots).
- Convert units contextually — show both metric and imperial where useful.
- When presenting lists of flights, prioritise by relevance: military first, then by altitude/speed.
- Always note the timestamp of data retrieval — this is live data that changes rapidly.
- Be concise for simple queries, comprehensive for reports and briefings.
""",
)


@mcp.tool()
async def flights_near(lat: float, lon: float, radius_km: float = 100) -> list[dict]:
    """Get live flights near a geographic point via ADSB.lol real-time feed.

    Returns a list of flights, each containing: icao24, callsign, aircraft_type
    (commercial/military/private), model code, registration, latitude, longitude,
    altitude_m, velocity_ms, heading (degrees true), vertical_rate (m/s), squawk, and source.

    Args:
        lat: Latitude of center point (-90 to 90)
        lon: Longitude of center point (-180 to 180)
        radius_km: Search radius in kilometers (max ~100km due to API limits)
    """
    return await service.flights_near(lat, lon, radius_km)


@mcp.tool()
async def search_flight(query: str) -> list[dict]:
    """Search for a specific flight by callsign or ICAO24 hex code.

    Automatically detects the query type: 6-character hex strings are treated as
    ICAO24 codes (e.g. '4CA87A'), everything else as callsigns (e.g. 'RYR123', 'BAW456').

    Returns the same flight data structure as flights_near. Typically returns 0-1 results
    for hex lookups, possibly multiple for callsigns shared across codeshares.

    Args:
        query: Callsign (e.g. 'RYR123') or ICAO24 hex code (e.g. '4CA87A')
    """
    return await service.search_flight(query)


@mcp.tool()
async def military_flights() -> list[dict]:
    """Get all currently airborne military aircraft worldwide.

    Sources data from ADSB.lol's dedicated military feed, which is unfiltered —
    unlike commercial flight trackers (e.g. FlightRadar24) that hide military
    and government aircraft. This is a key differentiator of Open Sky Intelligence.

    Returns the standard flight data structure with aircraft_type set to 'military'.
    Typically returns 50-300+ aircraft depending on time of day and global activity.
    """
    return await service.military_flights()


@mcp.tool()
async def flights_to(destination_icao: str) -> list[dict]:
    """Find current flights heading to a destination airport.

    Uses cached route data from hexdb.io, cross-referenced with live flight positions.
    Results depend on routes previously looked up and cached — coverage improves over time
    as more callsigns are queried.

    Args:
        destination_icao: ICAO airport code, e.g. 'EHAM' (Amsterdam Schiphol),
            'EGLL' (London Heathrow), 'KJFK' (New York JFK), 'VGHS' (Dhaka Shahjalal)
    """
    return await service.flights_to(destination_icao)


@mcp.tool()
async def flights_from(origin_icao: str) -> list[dict]:
    """Find current flights that departed from an origin airport.

    Uses cached route data from hexdb.io, cross-referenced with live flight positions.
    Results depend on routes previously looked up and cached — coverage improves over time
    as more callsigns are queried.

    Args:
        origin_icao: ICAO airport code, e.g. 'EHAM' (Amsterdam Schiphol),
            'EGLL' (London Heathrow), 'KJFK' (New York JFK), 'VCBI' (Colombo Bandaranaike)
    """
    return await service.flights_from(origin_icao)


@mcp.tool()
async def aircraft_info(icao24: str) -> dict | None:
    """Get detailed aircraft metadata by ICAO24 hex transponder code.

    Returns: manufacturer (e.g. 'Airbus', 'Boeing'), type_name (e.g. 'A319 111'),
    type_code (e.g. 'A319'), registration (e.g. 'G-EZBZ'), owner (e.g. 'easyJet UK'),
    and operator_code. Data sourced from hexdb.io and cached locally for 30 days.

    Returns None if the aircraft is not found in the database.

    Args:
        icao24: ICAO24 hex transponder code (e.g. '4CA87A', '4010EE')
    """
    return await service.aircraft_info(icao24)


@mcp.tool()
async def get_satellites(category: str | None = None) -> list[dict]:
    """Get current satellite positions propagated from TLE orbital data.

    Returns: norad_id, name, category, latitude, longitude, altitude_km,
    speed_ms, and inclination for each satellite.

    Available categories: 'iss' (International Space Station + visitors),
    'military', 'weather', 'nav' (GNSS/GPS), 'science', 'starlink'.
    Omit category to get all tracked satellites.

    Positions are computed in real-time using SGP4 propagation from Celestrak TLE data,
    refreshed hourly.

    Args:
        category: Filter by satellite category, or None for all
    """
    return await service.get_satellites(category)


@mcp.tool()
async def get_weather(lat: float, lon: float) -> dict | None:
    """Get current weather conditions at any location worldwide.

    Returns: temperature_c, feels_like_c, humidity_pct, wind_speed_kt,
    wind_direction (degrees), wind_gusts_kt, cloud_cover_pct, visibility_m,
    precipitation_mm, weather_code (WMO), and human-readable description.

    Data sourced from Open-Meteo API (no API key required). Useful for providing
    atmospheric context when reporting on flights or locations.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
    """
    return await service.get_weather(lat, lon)


@mcp.tool()
async def get_status() -> dict:
    """Get Open Sky Intelligence system health and diagnostics.

    Returns: system status, flight poll count, last poll totals (total flights
    and military count), and number of cached satellite TLEs. Use this to verify
    the system is operational and data is flowing.
    """
    return await service.get_status()
