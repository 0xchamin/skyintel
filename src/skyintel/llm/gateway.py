"""LiteLLM gateway — tool-calling loop with BYOK credentials."""

import json
import logging
import asyncio as _asyncio

from skyintel import service
from skyintel.config import get_settings

logger = logging.getLogger(__name__)

# LiteLLM model prefixes per provider
PROVIDER_PREFIX = {
    "anthropic": "anthropic/",
    "openai": "",
    "google": "gemini/",
}

MAX_RESULT_ITEMS = 500

# ── Tool call tracking (for /playground) ──
_tool_call_counts = {}

def get_tool_call_counts() -> dict:
    return dict(_tool_call_counts)

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
                    "max_results": {"type": "integer", "description": "Max results to return (default 50)", "default": 50},
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
                    "max_results": {"type": "integer", "description": "Max results to return (default 50)", "default": 50},
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
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Max results to return (default 50)", "default": 50},
                },
            },
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
                    "max_results": {"type": "integer", "description": "Max results to return (default 50)", "default": 50},
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
                    "max_results": {"type": "integer", "description": "Max results to return (default 50)", "default": 50},
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
                    "max_results": {"type": "integer", "description": "Max results to return (default 50)", "default": 50},
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
    {
        "type": "function",
        "function": {
            "name": "iss_position",
            "description": "Get the current real-time position of the International Space Station — latitude, longitude, altitude, speed.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "iss_crew",
            "description": "Get the current crew aboard the International Space Station — names and count.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "iss_passes",
            "description": "Predict upcoming ISS passes visible from a ground location. Returns rise/set times, max elevation, duration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Observer latitude (-90 to 90)"},
                    "lon": {"type": "number", "description": "Observer longitude (-180 to 180)"},
                    "hours": {"type": "integer", "description": "Lookahead window in hours (default 24)", "default": 24},
                    "min_elevation": {"type": "number", "description": "Minimum peak elevation in degrees (default 10)", "default": 10.0},
                },
                "required": ["lat", "lon"],
            },
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
    "iss_position": service.iss_position,
    "iss_crew": service.iss_crew,
    "iss_passes": service.iss_passes,
}

def _configure_langfuse():
    """Configure LangFuse OTEL callbacks for LiteLLM if keys are set."""
    settings = get_settings()
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        import litellm
        import os
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
        os.environ["LANGFUSE_OTEL_HOST"] = settings.langfuse_otel_host
        litellm.callbacks = ["langfuse_otel"]
        logger.info("LangFuse OTEL observability enabled")

_configure_langfuse()


SYSTEM_PROMPT = """You are an expert aviation and space intelligence analyst powered by Open Sky Intelligence.

You have access to real-time tools for flight tracking, military aircraft monitoring, satellite positions,
aircraft metadata, and weather. Use aviation terminology accurately.

When generating reports, use well-structured HTML with inline CSS (dark theme).
Always note timestamps — this is live data. Prioritise military flights in listings."""

SYSTEM_PROMPT_CLI = SYSTEM_PROMPT.replace(
    "When generating reports, use well-structured HTML with inline CSS (dark theme).",
    "When generating reports, use clean markdown formatting — tables, headers, bullet points. No HTML."
)

MAX_TOOL_ROUNDS = 10


def _truncate_result(result):
    """Safety net — truncate if results still too large."""
    if isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
        if len(result["results"]) > MAX_RESULT_ITEMS:
            result = {
                **result,
                "results": result["results"][:MAX_RESULT_ITEMS],
                "truncated": True,
                "note": f"Showing top {MAX_RESULT_ITEMS} of {result.get('total_count', '?')} results."
            }
        return json.dumps(result, default=str)
    if isinstance(result, list) and len(result) > MAX_RESULT_ITEMS:
        return json.dumps({
            "results": result[:MAX_RESULT_ITEMS],
            "total_count": len(result),
            "truncated": True,
            "note": f"Showing top {MAX_RESULT_ITEMS} of {len(result)} results."
        }, default=str)
    return json.dumps(result, default=str)


async def execute_tool(name: str, args: dict):
    """Execute a tool call and return the result as a JSON string."""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = await handler(**args)
        return _truncate_result(result)
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e)
        return json.dumps({"error": str(e)})


async def chat(
    messages: list[dict],
    provider: str,
    api_key: str,
    model: str,
    output_format: str = "html",
) -> str:
    """Run a chat completion with tool-calling loop.

    Args:
        messages: Chat history [{role, content}, ...]
        provider: 'anthropic', 'openai', or 'google'
        api_key: User's API key (from localStorage, never stored)
        model: Model name (e.g. 'claude-sonnet-4-20250514')
        output_format: 'html' for web chat, 'markdown' for CLI

    Returns:
        Final assistant text response.
    """
    from litellm import acompletion

    prefix = PROVIDER_PREFIX.get(provider, "")
    litellm_model = f"{prefix}{model}"

    prompt = SYSTEM_PROMPT_CLI if output_format == "markdown" else SYSTEM_PROMPT
    full_messages = [{"role": "system", "content": prompt}] + messages

    for _ in range(MAX_TOOL_ROUNDS):
        for attempt in range(3):
            try:
                response = await acompletion(
                    model=litellm_model,
                    messages=full_messages,
                    tools=TOOLS,
                    api_key=api_key,
                )
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < 2:
                    wait = (attempt + 1) * 30
                    logger.warning("Rate limited, retrying in %ds (attempt %d/3)", wait, attempt + 1)
                    await _asyncio.sleep(wait)
                else:
                    raise

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or (choice.message.tool_calls and len(choice.message.tool_calls) > 0):
            full_messages.append(choice.message.model_dump())

            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                logger.info("Tool call: %s(%s)", tc.function.name, args)
                _tool_call_counts[tc.function.name] = _tool_call_counts.get(tc.function.name, 0) + 1
                result = await execute_tool(tc.function.name, args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            return choice.message.content or ""

    return "I reached the maximum number of tool calls. Please try a simpler query."

async def chat_stream(
    messages: list[dict],
    provider: str,
    api_key: str,
    model: str,
):
    """Run chat with tool-calling loop, then stream the final response.

    Yields SSE-formatted strings: 'data: {chunk}\n\n'
    Tool calls are resolved server-side before streaming begins.
    """
    from litellm import acompletion

    prefix = PROVIDER_PREFIX.get(provider, "")
    litellm_model = f"{prefix}{model}"

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    # ── Resolve all tool calls (non-streaming) ──
    for _ in range(MAX_TOOL_ROUNDS):
        for attempt in range(3):
            try:
                response = await acompletion(
                    model=litellm_model,
                    messages=full_messages,
                    tools=TOOLS,
                    api_key=api_key,
                )
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < 2:
                    wait = (attempt + 1) * 30
                    logger.warning("Rate limited, retrying in %ds (attempt %d/3)", wait, attempt + 1)
                    await _asyncio.sleep(wait)
                else:
                    raise

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or (choice.message.tool_calls and len(choice.message.tool_calls) > 0):
            full_messages.append(choice.message.model_dump())

            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                logger.info("Tool call: %s(%s)", tc.function.name, args)
                _tool_call_counts[tc.function.name] = _tool_call_counts.get(tc.function.name, 0) + 1
                result = await execute_tool(tc.function.name, args)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # Signal tool activity to client
            yield f"data: {json.dumps({'type': 'status', 'content': '🔍 Analysing data...'})}\n\n"
        else:
            # No more tool calls — stream the final response
            break
    else:
        yield f"data: {json.dumps({'type': 'text', 'content': 'I reached the maximum number of tool calls. Please try a simpler query.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # ── Stream the final LLM response ──
    try:
        stream = await acompletion(
            model=litellm_model,
            messages=full_messages,
            tools=TOOLS,
            api_key=api_key,
            stream=True,
        )

        async for chunk in stream:
            try:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = choices[0].delta
                if delta and getattr(delta, "content", None):
                    yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"
            except (IndexError, AttributeError):
                continue

    except Exception as e:
        logger.error("Stream failed: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    yield "data: [DONE]\n\n"


