# 🔭 Open Sky Intelligence

Real-time flight tracking, military aircraft monitoring, satellite positions, and AI-powered airspace intelligence — all in one platform.

[![PyPI](https://img.shields.io/pypi/v/skyintel)](https://pypi.org/project/skyintel/)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Features

- 🌍 **Live 3D Globe** — CesiumJS with real-time aircraft and satellite rendering
- ✈️ **Flight Tracking** — Commercial, military, and private aircraft worldwide
- ⚔️ **Unfiltered Military** — See aircraft hidden by commercial trackers
- 🛰 **Satellite Tracking** — ISS, military, weather, navigation, science, Starlink
- 🤖 **AI Chat (BYOK)** — Ask questions in natural language using your own LLM API key
- 🔧 **MCP Tools** — 9 tools for Claude Desktop, VS Code, and other MCP clients
- 🗺 **Multiple Map Layers** — Dark, satellite imagery, streets, 3D terrain
- 📤 **Shareable Snapshots** — Share your view via URL or native share sheet
- 🌤 **Weather** — Real-time conditions at any clicked location

## Quick Start

```bash
pip install skyintel
skyintel init
skyintel serve
```

Open http://localhost:9096 in your browser.

## Configuration

Create a `.env` file in your project directory:

```env
# Required — OpenSky Network OAuth2 credentials
# Register at https://opensky-network.org
SKYINTEL_OPENSKY_CLIENT_ID=your_client_id
SKYINTEL_OPENSKY_CLIENT_SECRET=your_client_secret

# Optional — Cesium Ion token (enables 3D terrain layer)
# Get a free token at https://ion.cesium.com
SKYINTEL_CESIUM_ION_TOKEN=your_token

# Optional — Server config
SKYINTEL_HOST=0.0.0.0
SKYINTEL_PORT=9096
SKYINTEL_FLIGHT_POLL_INTERVAL=30
SKYINTEL_SATELLITE_POLL_INTERVAL=3600
```

## CLI Commands

```bash
skyintel serve                           # Start the server
skyintel serve --stdio                   # MCP stdio mode (Claude Desktop)
skyintel status                          # Show system status
skyintel init                            # Initialize database
skyintel config                          # Show current config

skyintel flights --military              # List military flights
skyintel flights --search RYR123         # Search by callsign
skyintel flights --lat 51 --lon -0.5     # Flights near a point
skyintel satellites --category iss       # List ISS objects
skyintel above --lat 51 --lon -0.5       # Flights + satellites above

skyintel mcp-config                      # MCP config for Claude Desktop
skyintel mcp-config --vscode             # MCP config for VS Code
skyintel mcp-config --stdio              # MCP config for stdio mode
```

## AI Chat (BYOK)

Open Sky Intelligence includes an in-app AI chat that works with your own LLM API key. Click **⚙ Settings** in the toolbar to configure:

**Supported providers:**
- **Claude** (Anthropic) — `claude-sonnet-4-20250514`
- **GPT** (OpenAI) — `gpt-4o`
- **Gemini** (Google) — `gemini-2.0-flash`

**Privacy:** Your API key is stored in your browser's localStorage only — it is never sent to or stored on the Open Sky Intelligence server. Chat history is also stored in localStorage only (max 50 messages).

## MCP Integration

Open Sky Intelligence exposes 9 tools via the Model Context Protocol for use with Claude Desktop, VS Code Copilot, and other MCP clients.

### Setup — Streamable HTTP (recommended)

Start the server (`skyintel serve`), then add to your MCP config:

**Claude Desktop / Cursor** (`mcp.json`):
```json
{
  "mcpServers": {
    "skyintel": {
      "url": "http://localhost:9096/mcp"
    }
  }
}
```

**VS Code** (`.vscode/mcp.json`):
```json
{
  "servers": {
    "skyintel": {
      "url": "http://localhost:9096/mcp"
    }
  }
}
```

### Setup — stdio mode

For Claude Desktop running the server as a subprocess:

```json
{
  "mcpServers": {
    "skyintel": {
      "command": "skyintel",
      "args": ["serve", "--stdio"]
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `flights_near` | Live flights near a location (lat/lon/radius) |
| `search_flight` | Find a flight by callsign or ICAO24 hex |
| `military_flights` | All military aircraft worldwide (unfiltered) |
| `flights_to` | Flights heading to an airport (ICAO code) |
| `flights_from` | Flights departed from an airport (ICAO code) |
| `aircraft_info` | Aircraft metadata (manufacturer, type, owner) |
| `get_satellites` | Satellite positions by category |
| `get_weather` | Weather conditions at any location |
| `get_status` | System health and diagnostics |

## Data Sources

| Source | Data | Auth |
|--------|------|------|
| [ADSB.lol](https://api.adsb.lol) | Live flights (on-demand) | None |
| [OpenSky Network](https://opensky-network.org) | Flight polling | OAuth2 |
| [hexdb.io](https://hexdb.io) | Aircraft metadata + routes | None |
| [Celestrak](https://celestrak.org) | Satellite TLEs | None |
| [Open-Meteo](https://open-meteo.com) | Weather | None |
| [Cesium Ion](https://ion.cesium.com) | 3D terrain tiles | Free token (optional) |

## Map Layers

| Layer | Source | Token |
|-------|--------|-------|
| 🌑 Dark | CARTO | None |
| 🛰 Satellite | ESRI World Imagery | None |
| 🗺 Streets | OpenStreetMap | None |
| ⛰ Terrain | Cesium World Terrain | Cesium Ion (free) |

## Development

```bash
git clone https://github.com/youruser/skyintel.git
cd skyintel
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
skyintel init
skyintel serve
```

## License

MIT