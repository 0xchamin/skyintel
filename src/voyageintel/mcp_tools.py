"""MCP tools for Open Sky Intelligence — streamable HTTP + stdio."""

from fastmcp import FastMCP

from voyageintel import service

mcp = FastMCP(
    name="VoyageIntel",
    instructions="""You are an expert multi-domain intelligence analyst with access to real-time data through VoyageIntel tools spanning air, sea, and space.

## Your Capabilities
- Live flight tracking worldwide (commercial, military, private)
- Unfiltered military aircraft monitoring (a key differentiator — most commercial trackers hide these)
- Real-time vessel tracking via AIS (cargo, tanker, passenger, military, fishing, recreational)
- Port monitoring and vessel routing
- Satellite position tracking across 6 categories (ISS, military, weather, navigation, science, Starlink)
- Aircraft metadata enrichment (manufacturer, type, owner, registration)
- Flight route lookup (origin/destination airports)
- Marine and aviation weather
- Geocoding — resolve place names to coordinates
- Cross-domain correlation — military aircraft + naval vessels in same area

## Tool Selection Guidelines
- **flights_near**: Use when the user asks about flights over/above/near a location. You know world geography — convert place names to lat/lon coordinates yourself.
- **search_flight**: Use when the user mentions a specific callsign (e.g. 'RYR123'), ICAO24 hex code, or registration.
- **military_flights**: Use for any query about military, government, or defense-related air activity.
- **flights_to / flights_from**: Use when the user asks about flights heading to or departing from a specific airport. Convert airport names to ICAO codes yourself.
- **aircraft_info**: Use to enrich any flight with detailed aircraft metadata. Always call this when generating reports.
- **vessels_near**: Use when the user asks about ships/vessels near a location.
- **search_vessel**: Use when the user mentions a specific vessel name, MMSI, or IMO number.
- **military_vessels**: Use for any query about naval vessels or military ships.
- **vessels_by_type**: Use when the user asks about a specific vessel category (cargo, tanker, passenger, fishing, etc).
- **vessels_to / vessels_from**: Use for vessel routing queries — heading to a destination or near/departing a port.
- **vessel_info**: Use to get detailed info on a specific vessel by MMSI.
- **port_info / ports_near**: Use for port queries — details by code or nearby ports.
- **sea_weather**: Use for marine conditions — waves, swell, sea temp. Use this for ocean locations.
- **get_weather**: Use for land/aviation weather. Use this for airports and land locations.
- **activity_near**: Use when the user wants ALL activity (flights + vessels) near a location.
- **military_activity**: Use when the user asks about military presence — returns both aircraft and naval vessels.
- **geocode**: Use to resolve place names to exact coordinates when you're unsure of the lat/lon.
- **get_satellites**: Use for satellite queries. Pass a category filter when the user specifies one.
- **get_status**: Use only when asked about system health or diagnostics.

## Domain Awareness
- Use knots and nautical miles for maritime distances/speeds
- Use metres/second and feet for aviation altitude/speed
- When asked about "military activity" check BOTH aircraft and vessels
- Convert place names to coordinates yourself — you know world geography
- Use the geocode tool when you need precise coordinates for less common locations

## Report Generation
When asked to generate a report:
1. Gather data by calling multiple tools — flights, vessels, aircraft metadata, satellites, weather as relevant.
2. Synthesise into well-structured, visually rich HTML5 with inline CSS (dark theme).
3. Include tables, summary statistics, and contextual narrative.
4. Add timestamps (UTC) and source attribution.
5. For maritime, use knots for speed and nautical miles for distance.

## Response Style
- Use aviation terminology accurately (FL350 = Flight Level 350 = ~35,000ft, kt = knots).
- Use maritime terminology accurately (MMSI, IMO, COG, SOG, draught).
- Convert units contextually — show both metric and imperial where useful.
- Prioritise military assets in listings.
- Always note timestamps — this is live data that changes rapidly.
""",
)



@mcp.tool()
async def flights_near(lat: float, lon: float, radius_km: float = 100, max_results: int = 50) -> dict:


    """Get live flights near a geographic point via ADSB.lol real-time feed.

    Returns a list of flights, each containing: icao24, callsign, aircraft_type
    (commercial/military/private), model code, registration, latitude, longitude,
    altitude_m, velocity_ms, heading (degrees true), vertical_rate (m/s), squawk, and source.

    Args:
        lat: Latitude of center point (-90 to 90)
        lon: Longitude of center point (-180 to 180)
        radius_km: Search radius in kilometers (max ~100km due to API limits)
        max_results: Maximum number of results to return (default 50). Use a higher value if user asks for above 50 (e.g. all, 100, etc.).

    """
    #return await service.flights_near(lat, lon, radius_km, max_results)
    return await service.flights_near(lat, lon, radius_km, max_results)


@mcp.tool()
async def search_flight(query: str, max_results: int = 50) -> dict:

    """Search for a specific flight by callsign or ICAO24 hex code.

    Automatically detects the query type: 6-character hex strings are treated as
    ICAO24 codes (e.g. '4CA87A'), everything else as callsigns (e.g. 'RYR123', 'BAW456').

    Returns the same flight data structure as flights_near. Typically returns 0-1 results
    for hex lookups, possibly multiple for callsigns shared across codeshares.

    Args:
        query: Callsign (e.g. 'RYR123') or ICAO24 hex code (e.g. '4CA87A')
    """
    return await service.search_flight(query, max_results)


@mcp.tool()
async def military_flights(max_results: int = 50) -> dict:

    """Get all currently airborne military aircraft worldwide.

    Sources data from ADSB.lol's dedicated military feed, which is unfiltered —
    unlike commercial flight trackers (e.g. FlightRadar24) that hide military
    and government aircraft. This is a key differentiator of Open Sky Intelligence.

    Returns the standard flight data structure with aircraft_type set to 'military'.
    Typically returns 50-300+ aircraft depending on time of day and global activity.

    Args:
        max_results: Maximum number of results to return (default 50). Use a higher value if user asks for above 50 (e.g. all, 100, etc.).
    """
    return await service.military_flights(max_results)

@mcp.tool()
async def flights_to(destination_icao: str, max_results: int = 50) -> dict:

    """Find current flights heading to a destination airport.

    Uses cached route data from hexdb.io, cross-referenced with live flight positions.
    Results depend on routes previously looked up and cached — coverage improves over time
    as more callsigns are queried.

    Args:
        destination_icao: ICAO airport code, e.g. 'EHAM' (Amsterdam Schiphol),
            'EGLL' (London Heathrow), 'KJFK' (New York JFK), 'VGHS' (Dhaka Shahjalal)
    """
    return await service.flights_to(destination_icao, max_results)


@mcp.tool()
async def flights_from(origin_icao: str, max_results: int = 50) -> dict:

    """Find current flights that departed from an origin airport.

    Uses cached route data from hexdb.io, cross-referenced with live flight positions.
    Results depend on routes previously looked up and cached — coverage improves over time
    as more callsigns are queried.

    Args:
        origin_icao: ICAO airport code, e.g. 'EHAM' (Amsterdam Schiphol),
            'EGLL' (London Heathrow), 'KJFK' (New York JFK), 'VCBI' (Colombo Bandaranaike)
    """
    return await service.flights_from(origin_icao, max_results)

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
async def get_satellites(category: str | None = None, max_results: int = 50) -> dict:


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
        max_results: Maximum number of results to return (default 50). Use a higher value if user asks for above 50 (e.g. all, 100, etc.).
    """
    return await service.get_satellites(category, max_results)


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

@mcp.tool()
async def iss_position() -> dict:
    """Get the current real-time position of the International Space Station.

    Returns: latitude, longitude, altitude_km, speed_ms, and orbital metadata.
    Position computed via SGP4 propagation from Celestrak TLE data refreshed hourly.
    """
    return await service.iss_position()


@mcp.tool()
async def iss_crew() -> dict:
    """Get the current crew aboard the International Space Station.

    Returns: list of crew members with names, and total count.
    Data sourced from Open Notify API.
    """
    return await service.iss_crew()


@mcp.tool()
async def iss_passes(lat: float, lon: float, hours: int = 24, min_elevation: float = 10.0) -> dict:
    """Predict upcoming ISS passes visible from a ground location.

    Returns rise/culmination/set times, azimuths, max elevation, and duration
    for each pass. Only passes with peak elevation above min_elevation are included.

    Args:
        lat: Observer latitude (-90 to 90)
        lon: Observer longitude (-180 to 180)
        hours: Lookahead window in hours (default 24)
        min_elevation: Minimum peak elevation in degrees to include (default 10)
    """
    return await service.iss_passes(lat, lon, hours, min_elevation)


@mcp.tool()
async def playground_guardrails() -> dict:
    """Get guardrail monitoring stats for the SkyIntel instance.

    Returns scan counts (input/output), blocked query count and block rate,
    scanner load status (loaded/lazy/unavailable), blocked counts per scanner,
    and the 20 most recent blocked queries (anonymised).

    Returns available=false on branches without LLM Guard installed.
    """
    return await service.get_playground_guardrails()

@mcp.tool()
async def playground_langfuse() -> dict:
    """Get LangFuse observability analytics for the SkyIntel instance.

    Returns total traces, average latency, token usage (input/output/total),
    estimated cost by model, tool call frequency, and daily metrics.
    Covers the last 30 days. Requires LangFuse keys to be configured.
    """
    return await service.get_playground_langfuse()

# ── Maritime Tools ───────────────────────────────────────────

@mcp.tool()
async def vessels_near(lat: float, lon: float, radius_km: float = 50, max_results: int = 50) -> dict:

    """Get live vessels near a geographic point via real-time AIS data.

    Returns a list of vessels, each containing: mmsi, imo, name, callsign,
    vessel_type (cargo/tanker/passenger/military/fishing/recreational/special/high_speed/unknown),
    flag_country, latitude, longitude, cog (course over ground), sog (speed in knots),
    heading, rot (rate of turn), nav_status, destination, eta, draught, length, width.

    Args:
        lat: Latitude of center point (-90 to 90)
        lon: Longitude of center point (-180 to 180)
        radius_km: Search radius in kilometers (default 50)
        max_results: Maximum number of results to return (default 50)
    """
    return await service.vessels_near(lat, lon, radius_km, max_results)


@mcp.tool()
async def search_vessel(query: str, max_results: int = 50) -> dict:

    """Search for a vessel by name, MMSI, or IMO number.

    Searches across vessel name (partial match), MMSI (exact), and IMO (exact).
    Returns the same vessel data structure as vessels_near.

    Args:
        query: Vessel name (e.g. 'Ever Given'), MMSI (e.g. '353136000'), or IMO (e.g. '9811000')
        max_results: Maximum number of results to return (default 50)
    """
    return await service.vessel_search(query, max_results)


@mcp.tool()
async def military_vessels(max_results: int = 50) -> dict:

    """Get all tracked military and naval vessels worldwide.

    Sources data from AIS feeds — note that many military vessels disable or limit
    AIS transmission, so this represents only vessels actively broadcasting.
    Classification is based on AIS ship type codes (35-39) and vessel name patterns
    (USS, HMS, HMAS, etc.).

    Args:
        max_results: Maximum number of results to return (default 50)
    """
    return await service.military_vessels_list(max_results)


@mcp.tool()
async def vessels_by_type(vessel_type: str, max_results: int = 50) -> dict:

    """Get vessels filtered by type category.

    Valid types: cargo, tanker, passenger, military, fishing, recreational,
    special, high_speed, unknown.

    Args:
        vessel_type: Vessel category to filter by (e.g. 'tanker', 'cargo', 'fishing')
        max_results: Maximum number of results to return (default 50)
    """
    return await service.vessels_by_type(vessel_type, max_results)


@mcp.tool()
async def vessels_to(destination: str, max_results: int = 50) -> dict:

    """Find vessels heading to a destination port or area.

    Searches the AIS destination field, which is free-text set by the vessel's crew.
    Common formats include port codes (e.g. 'NLRTM' for Rotterdam), port names,
    or abbreviated forms. Partial matching is supported.

    Args:
        destination: Destination to search for (e.g. 'ROTTERDAM', 'NLRTM', 'SINGAPORE')
        max_results: Maximum number of results to return (default 50)
    """
    return await service.vessels_to(destination, max_results)


@mcp.tool()
async def vessels_from(port_code: str, radius_km: float = 25, max_results: int = 50) -> dict:

    """Find vessels near or departing from a port.

    Uses the port's coordinates from the World Port Index database to find
    vessels within a radius. Useful for monitoring port activity and departures.

    Args:
        port_code: UN/LOCODE port code (e.g. 'USLAX' for Los Angeles,
            'SGSIN' for Singapore, 'NLRTM' for Rotterdam, 'GBSOU' for Southampton)
        radius_km: Search radius around the port in kilometers (default 25)
        max_results: Maximum number of results to return (default 50)
    """
    return await service.vessels_from(port_code, radius_km, max_results)


@mcp.tool()
async def vessel_info(mmsi: str) -> dict | None:

    """Get detailed vessel information by MMSI (Maritime Mobile Service Identity).

    Returns full vessel data including identity (name, IMO, callsign), classification
    (type, flag state), position, motion (COG, SOG, heading, rate of turn),
    navigation status, destination, ETA, dimensions (length, width, draught).

    Args:
        mmsi: Maritime Mobile Service Identity — 9-digit identifier (e.g. '353136000')
    """
    return await service.vessel_info(mmsi)


@mcp.tool()
async def port_info(port_code: str) -> dict | None:

    """Get port details by UN/LOCODE.

    Returns port name, country, coordinates, type (seaport/river_port/offshore),
    and size (large/medium/small) from the World Port Index database.

    Args:
        port_code: UN/LOCODE port code (e.g. 'USLAX', 'SGSIN', 'DEHAM', 'CNSHA')
    """
    return await service.port_info(port_code)


@mcp.tool()
async def ports_near(lat: float, lon: float, radius_km: float = 50, max_results: int = 20) -> dict:

    """Find ports near a geographic location.

    Searches the World Port Index database (~400 ports worldwide) for ports
    within a radius of a point. Results are sorted by proximity.

    Args:
        lat: Latitude of center point (-90 to 90)
        lon: Longitude of center point (-180 to 180)
        radius_km: Search radius in kilometers (default 50)
        max_results: Maximum number of results to return (default 20)
    """
    return await service.ports_near(lat, lon, radius_km, max_results)


@mcp.tool()
async def sea_weather(lat: float, lon: float) -> dict | None:

    """Get marine weather conditions at an ocean location.

    Returns wave height, wave direction, wave period, swell height, swell direction,
    swell period, wind wave data, and ocean current velocity/direction.
    Use this for ocean and coastal locations — use get_weather for land/airport weather.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
    """
    return await service.sea_weather(lat, lon)


# ── Cross-Domain Tools ───────────────────────────────────────

@mcp.tool()
async def activity_near(lat: float, lon: float, radius_km: float = 100, max_results: int = 50) -> dict:

    """Get all activity near a geographic point — flights AND vessels combined.

    Returns both flight and vessel data in a single response. Use this when the user
    wants a complete picture of activity in an area, or when they don't specify
    whether they mean air or sea traffic.

    Args:
        lat: Latitude of center point (-90 to 90)
        lon: Longitude of center point (-180 to 180)
        radius_km: Search radius in kilometers (default 100)
        max_results: Maximum results per domain (default 50)
    """
    return await service.activity_near(lat, lon, radius_km, max_results)


@mcp.tool()
async def military_activity(lat: float, lon: float, radius_km: float = 200, max_results: int = 50) -> dict:

    """Get all military assets near a geographic point — aircraft AND naval vessels.

    Combines military aircraft from ADSB.lol's unfiltered military feed with
    naval vessels from AIS data. Use this whenever the user asks about military
    presence, defense activity, or naval operations in an area.

    Args:
        lat: Latitude of center point (-90 to 90)
        lon: Longitude of center point (-180 to 180)
        radius_km: Search radius in kilometers (default 200)
        max_results: Maximum results per domain (default 50)
    """
    return await service.military_activity(lat, lon, radius_km, max_results)


@mcp.tool()
async def geocode(place_name: str) -> dict | None:

    """Resolve a place name to geographic coordinates using Google Maps Geocoding.

    Results are cached for 30 days. Use this when you need precise coordinates
    for less common locations, straits, channels, or ambiguous place names.
    For well-known cities and airports, you can use your built-in geography knowledge instead.

    Args:
        place_name: Place name to geocode (e.g. 'Strait of Hormuz', 'Port of Rotterdam',
            'Suez Canal', 'Malacca Strait')
    """
    return await service.geocode(place_name)


@mcp.tool()
async def playground_system() -> dict:

    """Get unified system health metrics across all domains — air, sea, and space.

    Returns flight counts (commercial/military/private), vessel counts by type,
    satellite cache stats, AIS WebSocket status, polling health, database size,
    and data source status. Use only when asked about system health or diagnostics.
    """
    return await service.get_playground_system()
