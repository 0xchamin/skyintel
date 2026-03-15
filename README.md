# 🔭 Open Sky Intelligence

**Real-time flight, military aircraft, and satellite tracking with AI-powered queries and an immersive 3D globe.**

[![PyPI](https://img.shields.io/pypi/v/skyintel)](https://pypi.org/project/skyintel/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/skyintel/)

![Demo](demo.gif)

---

## Features

- 🌍 **3D Globe** — CesiumJS-powered immersive dark globe with real-time flight and satellite rendering
- ✈️ **Flight Tracking** — Live commercial, private, and military aircraft via ADSB.lol global feed (+ optional OpenSky Network for self-hosting)
- ⚔️ **Military Monitoring** — Unfiltered military aircraft feed — unlike commercial trackers that hide these (**FOR EDUCATIONAL PURPOSES ONLY**, these are public data)
- 🛰 **Satellite Tracking** — 6 categories (Space Stations, Military, Weather, Nav, Science, Starlink) via Celestrak + SGP4
- 🚀 **ISS Tracking** — Real-time position, crew info, pass predictions, and one-click Track ISS
- 🌤 **Weather** — Current conditions at any location via Open-Meteo
- 🤖 **MCP Server** — 15 tools via FastMCP, streamable HTTP + stdio for Claude Desktop / VS Code / Cursor
- 💬 **BYOK AI Chat** — Bring your own API key (Claude, OpenAI, Gemini) — keys stored in browser only
- ⚡ **SSE Streaming** — Server-Sent Events for real-time chat responses with incremental token rendering
- 🛡️ **Guardrails** — Layered chat safety via system prompt hardening + optional LLM Guard scanners
- 📊 **Playground Dashboard** — `/playground` — single pane of glass for system health, guardrail monitoring, and LangFuse analytics
- 🖥 **CLI** — Full command suite including `skyintel ask` for terminal-based AI queries
- 📈 **LangFuse Observability** — Optional LLM tracing, token tracking, and latency monitoring with dashboard integration

---

## Quick Start

### Install

```bash
# Recommended for MCP client integration (Claude Desktop, VS Code, etc.)
pipx install skyintel

# Or install in a virtual environment
pip install skyintel
```

> ⚠️ **`pipx` vs `pip`**: `pipx install` puts the `skyintel` command on your **global PATH** — required for MCP clients like Claude Desktop that spawn the process directly. `pip install` inside a virtual environment only makes the command available when the venv is activated. If you use `pip`, MCP clients will need the **full path** to the binary (e.g. `/path/to/venv/bin/skyintel`).

> ℹ️ `pip install skyintel` installs the `railway` branch version — ADSB.lol only, no OpenSky dependency. For the self-hosted version with OpenSky support, clone the `main` branch directly.

To upgrade an existing installation:

```bash
pipx upgrade skyintel
# or
pip install --upgrade skyintel
```

### Verify

```bash
skyintel --version      # Check installed version
skyintel --help         # View all commands
skyintel status         # Check configuration and system status
```

### Run

```bash
skyintel serve
```

Open [http://localhost:9096](http://localhost:9096) for the 3D globe and [http://localhost:9096/playground](http://localhost:9096/playground) for the observability dashboard.

### Configuration (optional)

SkyIntel works out of the box with **zero configuration** for basic flight and satellite tracking. API keys are only needed for specific features:

| Feature | Required Keys | Notes |
|---------|--------------|-------|
| 3D Globe + flights + satellites | None | Works immediately |
| Terrain layer | `SKYINTEL_CESIUM_ION_TOKEN` | Free from [cesium.com](https://cesium.com/ion/) |
| Web AI Chat | None (BYOK in browser) | Set your key in ⚙ Settings in the web UI |
| CLI `skyintel ask` | `SKYINTEL_LLM_PROVIDER`, `SKYINTEL_LLM_API_KEY`, `SKYINTEL_LLM_MODEL` | Stored in `.env` file |
| LangFuse observability | `SKYINTEL_LANGFUSE_PUBLIC_KEY`, `SKYINTEL_LANGFUSE_SECRET_KEY` | Free tier at [langfuse.com](https://langfuse.com) |
| OpenSky Network (`main` branch) | `SKYINTEL_OPENSKY_CLIENT_ID`, `SKYINTEL_OPENSKY_CLIENT_SECRET` | Not needed on `railway` branches |

Create a `.env` file if needed:

```env
# Server
SKYINTEL_HOST=0.0.0.0
SKYINTEL_PORT=9096

# OpenSky Network (main branch only — not needed for railway branches)
SKYINTEL_OPENSKY_CLIENT_ID=your_client_id
SKYINTEL_OPENSKY_CLIENT_SECRET=your_client_secret

# Cesium Ion (optional — enables terrain layer)
SKYINTEL_CESIUM_ION_TOKEN=your_token

# LLM — for CLI 'ask' command (optional, web chat uses browser localStorage)
SKYINTEL_LLM_PROVIDER=anthropic          # anthropic / openai / google
SKYINTEL_LLM_API_KEY=sk-ant-...
SKYINTEL_LLM_MODEL=claude-sonnet-4-20250514

# LangFuse (optional — LLM observability + playground analytics)
SKYINTEL_LANGFUSE_PUBLIC_KEY=pk-lf-...
SKYINTEL_LANGFUSE_SECRET_KEY=sk-lf-...
SKYINTEL_LANGFUSE_HOST=https://cloud.langfuse.com
SKYINTEL_LANGFUSE_OTEL_HOST=https://cloud.langfuse.com

# Playground (opt-in observability dashboard)
SKYINTEL_PLAYGROUND_ENABLED=true         # default: true

# Poll intervals
SKYINTEL_FLIGHT_POLL_INTERVAL=30         # 30s for main, 60s for railway
SKYINTEL_SATELLITE_POLL_INTERVAL=3600
```

> ℹ️ `.env.example` is only available when cloning the repo directly. For `pip`/`pipx` installs, create `.env` manually using the template above.

---

## Deployment Branches

SkyIntel ships three branches optimised for different environments:

| | `main` | `railway` | `railway-guardrails` |
|---|---|---|---|
| **Use case** | Self-hosting (home server, VPS, Raspberry Pi) | Cloud demo (Railway, Render, Fly.io) | Cloud demo + enhanced chat safety |
| **Flight data** | OpenSky Network + ADSB.lol | ADSB.lol global feed | ADSB.lol global feed |
| **Poll strategy** | OpenSky global + ADSB.lol military | Single ADSB.lol global call + `/v2/mil` | Single ADSB.lol global call + `/v2/mil` |
| **Poll interval** | 30s | 60s | 60s |
| **Coverage** | Global (OpenSky provides worldwide states) | ~7,500+ flights globally (depends on ADSB.lol feeder coverage) | ~7,500+ flights globally |
| **Guardrails** | System prompt only | System prompt only | System prompt + LLM Guard (BanTopics, Toxicity, InvisibleText) |
| **Extra memory** | — | — | ~500MB for guardrail models |
| **Military** | ADSB.lol `/v2/mil` | ADSB.lol `/v2/mil` (same) | ADSB.lol `/v2/mil` (same) |
| **Satellites/ISS** | ✅ Same | ✅ Same | ✅ Same |
| **AI Chat** | ✅ Same (ADSB.lol live queries) | ✅ Same (ADSB.lol live queries) | ✅ Same + guardrail scanning |
| **SSE Streaming** | ✅ Same | ✅ Same | ✅ Same |
| **Playground** | ✅ Same | ✅ Same | ✅ Same + guardrail stats |
| **PyPI** | — | ✅ `pip install skyintel` | — |

### Why multiple branches?

**OpenSky Network blocks cloud/datacenter IPs** — their API only responds to residential IPs, making it unusable on Railway, Render, and similar platforms. The `railway` branch replaces OpenSky with ADSB.lol's `/v2/point` endpoint for global flight data.

The `railway-guardrails` branch adds **LLM Guard** scanners for enhanced chat safety, at the cost of ~500MB additional memory (guardrail models are lazy-loaded on first chat request).

### ADSB.lol Coverage

ADSB.lol is a **crowdsourced network** of volunteer ADS-B feeders. Coverage is excellent in North America, Europe, and parts of Asia, but sparse in regions with fewer feeders (e.g. central China, much of Africa, central Russia). This is a data availability limitation of the volunteer feeder network, not something that can be resolved in code.

### Which should I use?

- **Running locally or on a VPS with a residential IP?** → Use `main`
- **Deploying to a cloud platform?** → Use `railway`
- **Cloud platform + you want chat guardrails?** → Use `railway-guardrails` (adds ~500MB memory)

---

## Architecture Overview

```mermaid
graph TB
    subgraph External["☁️ External Data Sources"]
        OS[OpenSky Network<br/>OAuth2 · Flight States<br/>main branch only]
        ADSB[ADSB.lol<br/>Global Feed · Military · Search]
        CT[Celestrak<br/>TLE Satellite Data]
        HEX[hexdb.io<br/>Aircraft Meta · Routes]
        OM[Open-Meteo<br/>Weather]
        ON[Open Notify<br/>ISS Crew]
        LF[LangFuse Cloud<br/>OTEL Traces · Analytics]
    end

    subgraph Backend["⚙️ Backend · Python · Starlette"]
        direction TB
        subgraph Pollers["Background Pollers"]
            FP[Flight Poller<br/>main: 30s OpenSky + /v2/mil<br/>railway: 60s Global + /v2/mil]
            SP[Satellite Poller<br/>1hr · Celestrak TLEs]
        end
        SVC[Service Layer<br/>service.py]
        API[REST API<br/>/api/*]
        MCP[MCP Server<br/>FastMCP · /mcp]
        GW[LLM Gateway<br/>LiteLLM · BYOK · SSE]
        GR[Guardrails<br/>LLM Guard · Lazy-loaded<br/>railway-guardrails only]
        PROP[SGP4 Propagator<br/>Skyfield]
        PG[Playground API<br/>/api/playground/*]
    end

    subgraph Storage["💾 SQLite · WAL Mode"]
        DB[(flights · satellites<br/>aircraft_meta · routes)]
    end

    subgraph Frontend["🌍 Web UI · Vanilla JS"]
        GLOBE[CesiumJS Globe<br/>BillboardCollection]
        DETAIL[Detail Panel<br/>Click-to-Inspect]
        CHAT[Chat Panel<br/>BYOK · SSE Streaming]
        DASH[Playground Dashboard<br/>System · Guardrails · LangFuse]
    end

    subgraph Clients["🔌 External Clients"]
        CLI[CLI<br/>skyintel ask/flights/iss]
        CD[Claude Desktop<br/>stdio]
        CC[Claude Code<br/>Streamable HTTP]
        VS[VS Code / Cursor<br/>Streamable HTTP]
    end

    OS -->|Poll every 30s<br/>main only| FP
    ADSB -->|Global + /v2/mil| FP
    CT -->|TLE fetch hourly| SP
    ON -->|On-demand| SVC
    FP --> DB
    SP --> DB

    DB --> API
    DB --> SVC
    ADSB -->|On-demand queries| SVC
    HEX -->|Cached lookups| SVC
    OM --> SVC
    PROP --> SVC

    SVC --> MCP
    SVC --> GW
    SVC --> CLI
    SVC --> PG
    GW --> GR
    GW -->|OTEL callbacks| LF
    LF -->|REST API reads| PG

    API --> GLOBE
    API --> DETAIL
    GW --> CHAT
    PG --> DASH

    MCP --> CD
    MCP --> CC
    MCP --> VS
```

SkyIntel is a **Python/Starlette backend** with a **vanilla JS + CesiumJS frontend** and no build step. Background pollers fetch flight data from ADSB.lol (global point query + military feed) and satellite TLEs from Celestrak on fixed intervals, storing results in a SQLite database with WAL mode for concurrent reads during writes. A shared **service layer** (`service.py`) provides unified query logic consumed by three surfaces: the REST API (globe + detail panel), the MCP server (Claude Desktop / VS Code / Cursor), and the CLI. The **LLM gateway** (`gateway.py`) implements a provider-agnostic tool-calling loop via LiteLLM, supporting Claude, OpenAI, and Gemini through a single BYOK interface — with SSE streaming for real-time token delivery. The `/playground` dashboard provides an observability surface with system metrics sourced from in-memory runtime stats, guardrail monitoring via the optional LLM Guard module (graceful degradation when absent), and LangFuse analytics via REST API reads. All flight classification (military, private, commercial) is performed through pattern-based heuristics in the classifier module, and satellite positions are computed locally via SGP4 propagation using Skyfield.

---

## MCP Client Setup

SkyIntel exposes 15 MCP tools via **two transports**:

| Transport | How it works | Used by |
|-----------|-------------|---------|
| **Streamable HTTP** (`/mcp`) | Client connects to a running SkyIntel server | Claude Code, VS Code, Cursor |
| **stdio** | MCP client spawns `skyintel` as a child process | Claude Desktop |

### Claude Desktop ✅ Tested

Claude Desktop uses **stdio** transport — it spawns `skyintel` as a child process.

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

**If installed via `pipx` (recommended):**

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

**If installed via `pip` in a virtual environment:**

```json
{
  "mcpServers": {
    "skyintel": {
      "command": "/full/path/to/.venv/bin/skyintel",
      "args": ["serve", "--stdio"]
    }
  }
}
```

Find your full path with `which skyintel` (macOS/Linux) or `where skyintel` (Windows).

**After saving**, restart Claude Desktop completely (quit and reopen). Look for the 🔌 tools icon — skyintel should appear with 15 tools.

**Troubleshooting:**
- Check logs: `cat ~/Library/Logs/Claude/mcp-server-skyintel.log`
- "No such file or directory" → use full path or install via `pipx`
- "Could not attach" → ensure no other `skyintel serve` is running on the same port

---

### Claude Code ✅ Tested

Claude Code uses **streamable HTTP** transport — it connects to a running SkyIntel server.

First, start the server:

```bash
skyintel serve
```

Then register the MCP server:

```bash
claude mcp add skyintel --transport http http://localhost:9096/mcp
```

Verify:

```bash
claude mcp list
```

Try asking: *"What military aircraft are currently airborne?"*

---

### VS Code + GitHub Copilot ✅ Tested

VS Code uses **streamable HTTP** transport via `.vscode/mcp.json`.

First, start the server:

```bash
skyintel serve
```

Then create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "skyintel": {
      "url": "http://localhost:9096/mcp"
    }
  }
}
```

Verify via Command Palette (Cmd+Shift+P): `MCP: List Servers` — skyintel should appear. Use **Agent mode** in Copilot Chat to access MCP tools.

Try asking: *"What flights are near London right now?"*

---

### Cursor ✅ Compatible

Cursor uses the same streamable HTTP transport as VS Code.

Start the server:

```bash
skyintel serve
```

Add to `.cursor/mcp.json`:

```json
{
  "servers": {
    "skyintel": {
      "url": "http://localhost:9096/mcp"
    }
  }
}
```

---

### Remote / Cloud Deployment

If SkyIntel is deployed on a cloud platform (e.g. Railway), remote MCP clients can connect directly:

**VS Code / Cursor:**
```json
{
  "servers": {
    "skyintel": {
      "url": "https://your-app.up.railway.app/mcp"
    }
  }
}
```

**Claude Code:**
```bash
claude mcp add skyintel --transport http https://your-app.up.railway.app/mcp
```

---

### Gemini CLI 🔜 Pending

Configuration pending — will be added once Gemini CLI MCP support is verified.

### OpenAI Codex 🔜 Pending

Configuration pending — will be added once Codex MCP support is verified.

---

### CLI Helper

Generate MCP config snippets directly:

```bash
skyintel mcp-config              # Claude Desktop (stdio)
skyintel mcp-config --stdio      # Claude Desktop (stdio, explicit)
skyintel mcp-config --vscode     # VS Code / Cursor (HTTP)
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `flights_near` | Live flights near a geographic point |
| `search_flight` | Search by callsign or ICAO24 hex |
| `military_flights` | All airborne military aircraft worldwide |
| `flights_to` | Flights heading to a destination airport |
| `flights_from` | Flights departed from an origin airport |
| `aircraft_info` | Aircraft metadata by ICAO24 hex |
| `get_satellites` | Satellite positions by category |
| `get_weather` | Current weather at any location |
| `get_status` | System health and diagnostics |
| `iss_position` | Real-time ISS position |
| `iss_crew` | Current ISS crew members |
| `iss_passes` | ISS pass predictions for a location |
| `playground_system` | System health metrics — flights, satellites, polling, DB, data sources |
| `playground_guardrails` | Guardrail scan/block stats — scanner status, recent blocks |
| `playground_langfuse` | LangFuse analytics — traces, tool call frequency |

---

## Architectural Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Dual-source data architecture** | Globe reads from SQLite (polled), Chat/MCP queries ADSB.lol live | Isolates polling from on-demand queries — avoids API rate limit contention, eliminates single point of failure, ensures globe rendering never competes with user queries |
| **BillboardCollection over Entity API** | CesiumJS BillboardCollection + LabelCollection | Entity API crashes at 25k+ objects. BillboardCollection handles 10k+ aircraft smoothly with canvas-based icon caching |
| **SQLite with WAL mode** | Single-file DB at `~/.skyintel/skyintel.db` | Zero-config, no external dependencies, WAL enables concurrent reads during writes. Sufficient for single-instance tracking workloads |
| **SGP4 propagation over external APIs** | Skyfield + sgp4 for satellite/ISS positions | Eliminates external API dependency for position data. TLEs refresh hourly from Celestrak, positions computed locally in real-time with sub-km accuracy |
| **Tool-calling loop with result capping** | Default 50 results per tool, `total_count` always returned | Prevents context window blowout (200k token limit) while giving the LLM accurate counts for reporting |
| **Chat history windowing** | Last 6 messages sent to LLM per request | Reduces input tokens per round-trip. Full history stays visible in UI. Clear chat for best results on complex queries |
| **Retry with exponential backoff** | 3 attempts, 30s/60s waits on rate limit errors | Gracefully handles per-minute token limits on free/low-tier LLM plans instead of failing with raw errors |
| **BYOK security model** | API keys in browser localStorage only | Keys never touch the server — sent per-request via POST body, never logged, never persisted server-side |
| **Cesium token masking** | Server-side injection via HTML template replacement | Token never exposed in any API response. Injected into `index.html` at serve time via `%%CESIUM_TOKEN%%` placeholder |
| **Vanilla JS, no build step** | Pure JS + CesiumJS CDN | Zero frontend toolchain complexity. No npm, no webpack, no transpilation. Deploy by copying files |
| **FastMCP dual transport** | Streamable HTTP (`/mcp`) + stdio mode | HTTP for remote/web clients (VS Code, Cursor, Claude Code), stdio for local desktop clients (Claude Desktop) |
| **LiteLLM as LLM gateway** | Unified API for Claude, OpenAI, Gemini | Single tool-calling implementation supports all major providers via provider prefixes |
| **LangFuse OTEL integration** | Optional observability via LiteLLM callbacks + REST API reads for playground | Zero-code tracing of every LLM call. OTEL ingestion for writes, REST API for dashboard reads. Single host, shared credentials |
| **SSE streaming (simple approach)** | Full tool-calling loop runs server-side, only the final LLM response is streamed | Avoids complex partial-stream/tool-call interleaving. Tool status messages sent during processing, final reply streamed token-by-token via Server-Sent Events |
| **Playground observability** | In-memory runtime stats + LangFuse REST API + graceful degradation | System metrics from `playground_runtime` dict (zero DB overhead), guardrail stats from LLM Guard module (ImportError fallback when absent), LangFuse analytics via REST API (returns `available: false` without keys) |
| **Tool call tracking** | In-memory counters in gateway.py | Accurate per-tool heatmap without LangFuse dependency. Tracks actual MCP tool names (not LiteLLM span names). Resets on restart — acceptable for operational monitoring |

### Guardrails Strategy

SkyIntel uses a **layered defense** approach for chat safety:

| Layer | Mechanism | Cost | Branch |
|-------|-----------|------|--------|
| **System prompt** | LLM instructed to only answer aviation/space topics | Zero — part of every request | All branches |
| **LLM Guard (lightweight)** | `BanTopics`, `Toxicity`, `InvisibleText` scanners | ~500MB model download on first chat | `railway-guardrails` only |
| **LLM Guard (full)** | Adds `PromptInjection`, `NoRefusal` scanners | ~1.3GB+ models — higher memory cost | Not shipped (see below) |

The heavy `PromptInjection` scanner (~738MB) and `NoRefusal` scanner (~827MB) were excluded in favour of system prompt hardening — a deliberate **cost/security tradeoff** for cloud deployments where memory is billed per GB/hour. The system prompt approach provides effective topic restriction at zero additional cost, while the lightweight scanners add defense-in-depth against invisible text attacks, toxic content, and off-topic abuse.

On the `railway-guardrails` branch, guardrail scan and block stats are tracked in-memory and surfaced in the `/playground` dashboard — including per-scanner block counts, block rate, and the 20 most recent blocked queries (anonymised).

### Aircraft Classification

Military and private aircraft detection in `classifier.py` uses **pattern-based heuristics**:

- **Military** — Detected via ICAO hex ranges, callsign prefixes, squawk codes, and the ADSB.lol `/v2/mil` feed
- **Private** — Detected via known private jet ICAO type codes (e.g. `GLF6`, `C680`, `CL35`, `LJ45`)

These patterns are maintained for **educational purposes** and are best-effort, not exhaustive. Contributions to improve classification accuracy are welcome — see `src/skyintel/flights/classifier.py` for the full ruleset.

---

## Data Sources

| Source | Used For | Auth | Polling | Notes |
|--------|----------|------|---------|-------|
| **OpenSky Network** | Primary flight data for globe (`main` branch only) | OAuth2 (required) | Every 30s | May block cloud/datacenter IPs. Not used on `railway` branches |
| **ADSB.lol** | Global flight data (`railway`), on-demand queries (all branches), military feed | None | 60s (`railway`) / On-demand | Crowdsourced — coverage depends on volunteer feeder density |
| **Celestrak** | Satellite TLE orbital data | None | Hourly | 6 categories: stations, military, weather, gnss, science, starlink |
| **hexdb.io** | Aircraft metadata + route lookup | None | Cached (30d/7d) | Can go down intermittently. Errors handled gracefully |
| **Open-Meteo** | Weather at any location | None | On-demand | Free, no API key required |
| **Open Notify** | ISS crew information | None | On-demand | Only reliable free source for current ISS crew |
| **LangFuse** | LLM observability + playground analytics | BYOK keys | OTEL callbacks + REST reads | Free tier. Trace count + tool heatmap surfaced in `/playground` |

> ⚠️ **Why different data for Globe vs Chat?** (`main` branch) The globe reads from SQLite (polled via OpenSky), while chat queries ADSB.lol live. This separation isolates polling from on-demand queries — avoids API rate limit contention and ensures globe rendering never competes with user queries. Flight counts may differ slightly — this is expected and by design.

> ℹ️ **Note:** On `railway` branches, both globe and chat use ADSB.lol as the data source, but the separation pattern remains: globe reads from SQLite (polled), chat queries the API directly.

---

## Playground Dashboard

The `/playground` route provides an **AI engineering observability surface** — a single pane of glass for system health, guardrail monitoring, and LangFuse analytics.

### System Metrics

- **Flights tracked** — total with commercial/military/private breakdown (from live poll data)
- **Satellites cached** — count and categories
- **Polling & uptime** — poll cycle count, uptime, poll intervals
- **Database** — SQLite file size, retention policy, path
- **Data source health** — live status for ADSB.lol, Celestrak, hexdb.io, Open-Meteo
- **LLM configuration** — provider, model, API key status, LangFuse status

### Guardrails Monitor

- **Scan counts** — input and output scans performed
- **Block rate** — blocked count and percentage
- **Scanner status** — loaded / lazy / unavailable for each scanner
- **Recent blocked queries** — last 20 blocked inputs (anonymised)
- Gracefully degrades to "available on railway-guardrails branch" when LLM Guard is not installed

### LangFuse Analytics

- **Chat sessions** — total trace count from LangFuse
- **Tool call frequency** — heatmap of MCP tool usage (in-memory tracking for accuracy)
- **Open LangFuse Dashboard** — one-click link to the full LangFuse UI
- Gracefully hidden when LangFuse keys are not configured

Auto-refreshes every 15 seconds. Dark theme, card-based grid, fully responsive.

---

## Web UI Guide

- **Globe** — Rotate, zoom, and pan the 3D globe. Flights and satellites render in real-time.
- **Toggle chips** — Enable/disable flight types (Commercial, Military, Private) and satellite categories (Space Stations, Military, Weather, Nav, Science, Starlink).
- **Click to inspect** — Click any flight or satellite for a detail panel with metadata, weather, and route info.
- **Track ISS** — Click the 🛰 Track ISS button in the status bar to rotate the globe to the ISS and open the crew/status panel.
- **Layers** — Switch between Dark, Satellite, Streets, and Terrain (terrain requires free Cesium Ion token).
- **Share** — Snapshot your current view and share via URL or Web Share API.
- **Chat** — Click the 💬 floating button to open the AI chat. Set your API key in ⚙ Settings first. Responses stream in real-time via SSE.
- **Playground** — Navigate to `/playground` for system health, guardrail stats, and LangFuse analytics.

> **Note:** Terrain view may take time to render.

> 💡 **Tip:** Clear chat history regularly for best performance on complex queries.

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `skyintel --version` | Show installed version |
| `skyintel serve` | Start server (MCP + REST + Web UI) |
| `skyintel serve --stdio` | MCP stdio mode for Claude Desktop |
| `skyintel status` | Show config and system status |
| `skyintel init` | Initialise database |
| `skyintel config` | Show current config as JSON |
| `skyintel ask "question"` | Ask the AI a question (uses .env credentials) |
| `skyintel ask "question" --provider anthropic --api-key sk-... --model claude-sonnet-4-20250514` | Ask with explicit credentials |
| `skyintel flights --military` | List military flights |
| `skyintel flights --search RYR123` | Search by callsign/hex |
| `skyintel flights --lat 51 --lon -0.5` | Flights near a point |
| `skyintel satellites --category iss` | List satellites by category |
| `skyintel above --lat 51 --lon -0.5` | Flights + satellites near a point |
| `skyintel iss` | ISS position + crew |
| `skyintel iss --passes --lat 51 --lon -0.5` | ISS pass predictions |
| `skyintel mcp-config` | Print MCP config for Claude Desktop |
| `skyintel mcp-config --vscode` | Print MCP config for VS Code |
| `skyintel mcp-config --stdio` | Print stdio MCP config |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| GET | `/playground` | Playground dashboard |
| GET | `/api/status` | System status + config |
| GET | `/api/flights?lat_min&lat_max&lon_min&lon_max` | Cached flights (bbox) |
| GET | `/api/aircraft/{icao24}` | Aircraft metadata |
| GET | `/api/route/{callsign}` | Flight route |
| GET | `/api/satellites?category=` | Satellite positions |
| GET | `/api/weather?lat=&lon=` | Current weather |
| GET | `/api/iss` | ISS position + crew |
| GET | `/api/iss/passes?lat=&lon=` | ISS pass predictions |
| POST | `/api/chat` | BYOK chat (messages, provider, api_key, model) |
| POST | `/api/chat/stream` | BYOK chat with SSE streaming |
| GET | `/api/playground/system` | System health metrics |
| GET | `/api/playground/guardrails` | Guardrail scan/block stats |
| GET | `/api/playground/langfuse` | LangFuse analytics |
| POST | `/mcp` | MCP streamable HTTP endpoint |

---

## Context Management & Rate Limits

Open Sky Intelligence uses a tool-calling architecture where the LLM makes multiple API calls per query. Each call carries the system prompt, tool definitions, and chat history. We've implemented several strategies to manage token usage:

- **Chat history windowing** — Only the last 6 messages are sent to the LLM per request, reducing input tokens while preserving context. Full history remains visible in the UI.
- **Result capping** — Tool results default to 50 items with `total_count` always returned, preventing context window blowout.
- **Retry with backoff** — Rate limit errors trigger automatic retries (up to 3 attempts, 30s/60s waits).
- **Dual system prompts** — Web chat uses HTML formatting, CLI uses markdown, keeping responses lean per surface.
- **SSE streaming** — Final LLM response streamed token-by-token via Server-Sent Events for perceived responsiveness. Tool-calling loop completes server-side before streaming begins.

> 💡 **Tip:** Clear chat history before complex queries for best results. Users on free-tier LLM plans should consider lighter models (e.g. `claude-haiku-4-20250514`, `gpt-4o-mini`).

> ⚠️ These are active areas of improvement. Contributions around smarter context summarisation and token counting are especially welcome.

---

## Roadmap

| Feature | Status |
|---------|--------|
| `/playground` dashboard — system metrics + guardrails monitor | ✅ Done |
| `/playground` dashboard — LangFuse analytics (traces, tool heatmap) | ✅ Done |
| SSE streaming responses | ✅ Done |
| Chat panel expand/collapse | ✅ Done |
| Claude Desktop MCP integration | ✅ Tested |
| Claude Code MCP integration | ✅ Tested |
| VS Code + GitHub Copilot MCP integration | ✅ Tested |
| LangFuse v2 Metrics API (latency, tokens, cost in playground) | 🔜 Planned |
| Guardrail threshold tuning + block rate improvement | 🔜 Planned |
| Additional MCP tools (private jets, flight history) | 🔜 Planned |
| Tool result caching — TTL-based (30-60s) on service layer | 🔜 Planned |
| Context window tracking — `tiktoken` token counting | 🔜 Planned |
| Hallucination detection — compare LLM response against tool results | 🔜 Planned |
| Flight history playback + time slider | 🔜 Planned |
| Flight pattern recognition + analytics | 🔜 Planned |
| Alert zones + notifications (browser/webhook) | 🔜 Planned |
| PostHog analytics | 🔜 Planned |
| E2E testing for PyPI install | 🔜 Planned |
| Raspberry Pi deployment guide | 🔜 Planned |
| Gemini CLI MCP support | 🔜 Pending verification |
| OpenAI Codex MCP support | 🔜 Pending verification |
| `flights_latest` upsert table (storage optimisation) | 🔜 Planned |
| Evaluation scoring (LangFuse Scores + DeepEval) | 🔮 Future |
| PII / Data masking (Presidio) | 🔮 Future |
| Rate limiting (slowapi) | 🔮 Future |
| Anomaly detection (scikit-learn IsolationForest) | 🔮 Future |
| Military activity trends (pandas + numpy) | 🔮 Future |
| Ship/vessel tracking (AIS — Open Nav Intelligence) | 🔮 Future |

---

## Contributing

Open Sky Intelligence is open source under the Apache 2.0 license. We welcome contributions:

- 🐛 **Bug reports** — Open an issue with reproduction steps
- 💡 **Feature requests** — Suggest ideas via GitHub Issues
- 🔧 **Pull requests** — Especially welcome in:
  - Context window optimisation
  - Additional data sources and enrichment
  - Aircraft classifier improvements (see `src/skyintel/flights/classifier.py`)
  - UI/UX improvements
  - Test coverage
  - Documentation

### Development Setup

```bash
git clone https://github.com/0xchamin/skyintel.git
cd skyintel
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # Add your API keys
skyintel serve
```

---

## Support the Project

If you find Open Sky Intelligence useful, consider supporting its development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/0xchamin)

⭐ **Star this repo** if you find it useful — it helps others discover the project.

---

## Enterprise

Need a managed deployment, custom integrations, SLA support, or additional data sources?

📧 **Let's talk** — reach out via [GitHub Issues](https://github.com/0xchamin/skyintel/issues) or [Buy Me a Coffee](https://buymeacoffee.com/0xchamin) to start a conversation.

---

## Coming Soon — Open Nav Intelligence

SkyIntel is evolving into **Open Nav Intelligence** — a unified real-time tracking platform spanning air, sea, and space.

```bash
pip install opennav
```

- 🌊 **Vessel Tracking** — AIS-powered ship monitoring worldwide
- 🛥️ **Submarine Detection** — Deep-sea intelligence layer
- ✈️ **Flight Tracking** — Everything SkyIntel does today
- 🛰️ **Satellite Tracking** — Full orbital awareness
- 🤖 **AI-Powered Queries** — Multi-domain natural language intelligence

Stay tuned.

---

## Disclaimer

Open Sky Intelligence is an **educational project and technical demonstration** showcasing real-time data integration, [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tool-calling patterns, and AI-powered geospatial intelligence.

All data is sourced from **publicly available open APIs** — no classified, proprietary, or restricted data is used. Flight positions come from [ADSB.lol](https://adsb.lol) and [OpenSky Network](https://opensky-network.org), satellite TLEs from [Celestrak](https://celestrak.org), ISS data from [Open Notify](http://open-notify.org), and weather from [Open-Meteo](https://open-meteo.com).

- Flight and satellite data is provided as-is from third-party sources. Accuracy, completeness, and availability are not guaranteed.
- Military aircraft data is sourced from publicly available ADS-B signals. Not all military aircraft broadcast ADS-B.
- Aircraft classification (military/private/commercial) is based on known patterns and heuristics — see `classifier.py` for details. This is for educational purposes only.
- ADSB.lol coverage depends on volunteer ADS-B feeder density — some regions (central China, much of Africa, central Russia) have limited coverage.
- ISS crew data is sourced from Open Notify and may not reflect real-time crew changes.
- LLM-generated reports and analyses are AI-assisted and should not be used as sole sources for operational, safety, or security decisions.
- BYOK API keys are stored in browser localStorage only — never persisted server-side. Users are responsible for their own API key security.

This project is not affiliated with any government, military, or intelligence agency. Aircraft and satellite positions shown are approximate and should **not** be used for navigation, safety-critical decisions, or operational purposes.

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

---

Built with ❤️ by [0xchamin](https://buymeacoffee.com/0xchamin)
