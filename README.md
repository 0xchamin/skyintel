# 🔭 Open Sky Intelligence

**Real-time flight, military aircraft, and satellite tracking with an immersive 3D globe.**

SkyIntel is a self-hosted, open-source MCP server and tactical web application that gives aviation enthusiasts, OSINT analysts, and military watchers a real-time, unfiltered view of everything in the sky.

![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen)

---

## ✨ Features

- **Live Flight Tracking** — real-time aircraft positions on a 3D globe at actual altitude
- **Military Aircraft Detection** — unfiltered military tracking via ADSB.lol + callsign/ICAO hex/squawk classifier
- **Satellite Tracking** — ISS, Starlink, military, weather, navigation, and science satellites
- **Immersive 3D Globe** — CesiumJS with dark tactical aesthetic, sun lighting, altitude layering
- **Smooth Interpolation** — dead-reckoning between polls so aircraft glide in real time
- **Click-to-Inspect** — detail panels for flights and satellites with full metadata
- **Fly-to View** — camera swoops to any aircraft or satellite with live weather overlay
- **Category Toggles** — filter by flight type (commercial/military/private) and satellite category
- **MCP Server** — AI-powered queries via Claude Desktop, VS Code, Gemini CLI *(coming soon)*
- **CLI** — command-line access to all data *(coming soon)*

## 📡 Data Sources

| Source | Role | Auth |
|--------|------|------|
| **ADSB.lol** | Primary — all global flights + military overlay | None |
| **OpenSky Network** | Supplementary metadata | OAuth2 (optional) |
| **Celestrak** | Satellite TLEs (ISS, Starlink, military, weather, nav, science) | None |
| **Open-Meteo** | Weather at aircraft locations | None |

## 🚀 Quick Start

```bash
pip install skyintel
skyintel serve
# Open http://localhost:9096
```

Works immediately with ADSB.lol + Celestrak — no API keys needed.

### Optional: OpenSky OAuth2 (higher rate limits)

Create a `.env` file:

```
SKYINTEL_OPENSKY_CLIENT_ID=your_client_id
SKYINTEL_OPENSKY_CLIENT_SECRET=your_client_secret
```

## 🖥️ Usage

### Web UI

Start the server and open `http://localhost:9096`:

```bash
skyintel serve
```

### CLI

```bash
skyintel status    # Show configuration and system status
skyintel init      # Initialise the database
skyintel config    # Display current configuration
skyintel serve     # Start the server (MCP + REST + Web UI)
```

### API

```bash
curl http://localhost:9096/api/status
curl http://localhost:9096/api/flights
curl "http://localhost:9096/api/satellites?category=military"
curl "http://localhost:9096/api/weather?lat=51.5&lon=-0.1"
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   SkyIntel                      │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ MCP      │  │ REST API │  │ Web UI       │  │
│  │ Server   │  │ /api/*   │  │ CesiumJS 3D  │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       └──────────────┴───────────────┘          │
│                      │                          │
│         ┌────────────┴─────────────┐            │
│         │   Background Pollers     │            │
│         │   Flights (30s)          │            │
│         │   Satellites (1hr)       │            │
│         └────────────┬─────────────┘            │
│              ┌───────┴────────┐                 │
│              │ Service Layer  │                 │
│              │ + Classifier   │                 │
│              │ + Propagator   │                 │
│              └───────┬────────┘                 │
│       ┌──────────────┼──────────────┐           │
│  ┌────┴─────┐  ┌─────┴─────┐  ┌────┴──────┐   │
│  │ SQLite   │  │ SQLite    │  │ Open-Meteo │   │
│  │ (flights)│  │ (sats)    │  │ (weather)  │   │
│  └────┬─────┘  └─────┬─────┘  └────────────┘   │
│       │               │                         │
│  ┌────┴─────┐  ┌─────┴─────┐                   │
│  │ ADSB.lol │  │ Celestrak │                   │
│  │ + OpenSky│  │           │                   │
│  └──────────┘  └───────────┘                   │
└─────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Component | Library |
|-----------|---------|
| MCP Server | FastMCP ≥3.1.0 |
| HTTP Client | httpx |
| Web Framework | Starlette + Uvicorn |
| CLI | Typer + Rich |
| Config | Pydantic Settings ≥2.0 |
| Database | aiosqlite (WAL mode) |
| Orbital Propagation | Skyfield + sgp4 |
| 3D Globe | CesiumJS 1.119 |
| Map Tiles | CARTO dark (no token) |

## ⚙️ Configuration

All settings via environment variables (prefix `SKYINTEL_`) or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKYINTEL_HOST` | `0.0.0.0` | Bind host |
| `SKYINTEL_PORT` | `9096` | Bind port |
| `SKYINTEL_DB_PATH` | `~/.skyintel/skyintel.db` | Database location |
| `SKYINTEL_OPENSKY_CLIENT_ID` | `None` | OpenSky OAuth2 client ID |
| `SKYINTEL_OPENSKY_CLIENT_SECRET` | `None` | OpenSky OAuth2 client secret |
| `SKYINTEL_FLIGHT_POLL_INTERVAL` | `30` | Flight poll interval (seconds) |
| `SKYINTEL_SATELLITE_POLL_INTERVAL` | `3600` | Satellite poll interval (seconds) |

## 🗺️ Roadmap

- [x] Live flight tracking (ADSB.lol + OpenSky)
- [x] Military aircraft detection + classifier
- [x] Satellite tracking (Celestrak + Skyfield)
- [x] 3D globe with altitude layering
- [x] Smooth dead-reckoning interpolation
- [x] Click-to-inspect panels
- [x] Fly-to with weather overlay
- [x] Category toggles (flights + satellites)
- [ ] MCP tools for AI assistants
- [ ] Full CLI commands
- [ ] Historical playback with time slider
- [ ] Watch zone alerts + notifications
- [ ] Web AI chat (BYOK)
- [ ] PyPI publish

## 📄 License

Apache 2.0