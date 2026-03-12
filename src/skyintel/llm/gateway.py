"""LiteLLM gateway — tool-calling loop with BYOK credentials."""

import json
import logging
#from litellm import acompletion

from skyintel import service

logger = logging.getLogger(__name__)

# LiteLLM model prefixes per provider
PROVIDER_PREFIX = {
    "anthropic": "anthropic/",
    "openai": "",
    "google": "gemini/",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "flights_near",
            "description": "Get live flights near a geographic point. Returns icao24, callsign, aircraft_type, model, registration, lat, lon, altitude_m, velocity_ms, heading, vertical_rate, squawk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude (-90 to 90)"},
                    "lon": {"type": "number", "description": "Longitude (-180 to 180)"},
                    "radius_km": {"type": "number", "description": "Radius in km (max ~100)", "default": 100},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_flight",
            "description": "Search for a flight by callsign (e.g. RYR123) or ICAO24 hex code (e.g. 4CA87A).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Callsign or ICAO24 hex"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "military_flights",
            "description": "Get all currently airborne military aircraft worldwide. Unfiltered — unlike commercial trackers.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flights_to",
            "description": "Find flights heading to a destination airport by ICAO code (e.g. EHAM, EGLL, KJFK).",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination_icao": {"type": "string", "description": "ICAO airport code"},
                },
                "required": ["destination_icao"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flights_from",
            "description": "Find flights departed from an origin airport by ICAO code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_icao": {"type": "string", "description": "ICAO airport code"},
                },
                "required": ["origin_icao"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aircraft_info",
            "description": "Get aircraft metadata — manufacturer, type, owner, registration — by ICAO24 hex code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "icao24": {"type": "string", "description": "ICAO24 hex transponder code"},
                },
                "required": ["icao24"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_satellites",
            "description": "Get satellite positions. Categories: iss, military, weather, nav, science, starlink.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category filter or null for all"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather at a location — temperature, wind, humidity, visibility, conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude"},
                    "lon": {"type": "number", "description": "Longitude"},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get system health — poll counts, cached data, operational status.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# Map tool names to service functions
TOOL_HANDLERS = {
    "flights_near": service.flights_near,
    "search_flight": service.search_flight,
    "military_flights": service.military_flights,
    "flights_to": service.flights_to,
    "flights_from": service.flights_from,
    "aircraft_info": service.aircraft_info,
    "get_satellites": service.get_satellites,
    "get_weather": service.get_weather,
    "get_status": service.get_status,
}

SYSTEM_PROMPT = """You are an expert aviation and space intelligence analyst powered by Open Sky Intelligence.

You have access to real-time tools for flight tracking, military aircraft monitoring, satellite positions,
aircraft metadata, and weather. Use aviation terminology accurately.

When generating reports, use well-structured HTML with inline CSS (dark theme).
Always note timestamps — this is live data. Prioritise military flights in listings.
Convert place names to coordinates yourself — you know world geography."""

MAX_TOOL_ROUNDS = 10


async def execute_tool(name: str, args: dict):
    """Execute a tool call and return the result as a JSON string."""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = await handler(**args)
        return json.dumps(result, default=str)
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e)
        return json.dumps({"error": str(e)})


async def chat(
    messages: list[dict],
    provider: str,
    api_key: str,
    model: str,
) -> str:
    from litellm import acompletion
    """Run a chat completion with tool-calling loop.

    Args:
        messages: Chat history [{role, content}, ...]
        provider: 'anthropic', 'openai', or 'google'
        api_key: User's API key (from localStorage, never stored)
        model: Model name (e.g. 'claude-sonnet-4-20250514')

    Returns:
        Final assistant text response.
    """
    prefix = PROVIDER_PREFIX.get(provider, "")
    litellm_model = f"{prefix}{model}"

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for _ in range(MAX_TOOL_ROUNDS):
        response = await acompletion(
            model=litellm_model,
            messages=full_messages,
            tools=TOOLS,
            api_key=api_key,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or (choice.message.tool_calls and len(choice.message.tool_calls) > 0):
            full_messages.append(choice.message.model_dump())

            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                logger.info("Tool call: %s(%s)", tc.function.name, args)
                result = await execute_tool(tc.function.name, args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            return choice.message.content or ""

    return "I reached the maximum number of tool calls. Please try a simpler query."
