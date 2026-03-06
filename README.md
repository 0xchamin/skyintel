# 🔭 OpenSkyAI

**Real-time flight, military aircraft, and satellite tracking with an immersive 3D globe.**

OpenSkyAI is a self-hosted, open-source MCP server and tactical web application that gives aviation enthusiasts, OSINT analysts, and military watchers a real-time, unfiltered view of everything in the sky.

![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen)
![Status](https://img.shields.io/badge/status-beta-orange)

---

## ✨ Features

- **🌍 3D Globe** — CesiumJS-powered dark tactical globe with real-time aircraft and satellites at actual altitude
- **✈️ Live Flight Tracking** — 10,000+ aircraft globally via ADSB.lol + OpenSky Network dual-source merge
- **⚔️ Military Aircraft** — Unfiltered military tracking via ADSB.lol + callsign/ICAO hex/squawk classifier
- **🛰 Satellite Tracking** — ISS, Starlink, military, weather, navigation, and science satellites via Celestrak TLEs
- **🎯 Category Toggles** — Filter flights (commercial/military/private) and satellite categories on/off
- **📋 Detail Panels** — Click any aircraft or satellite for full info (Material-styled slide-in panel)
- **📍 Fly-to View** — Camera swoops to any aircraft or satellite with one click
- **☁️ Weather Overlay** — Real-time weather at aircraft location via Open-Meteo
- **⬅ Camera History** — Return to previous viewpoint after fly-to
- **🔄 Dead-reckoning** — Smooth client-side interpolation between 30s server polls
- **🤖 MCP Server** — AI-powered queries via Claude Desktop, VS Code, Gemini CLI *(coming soon)*
- **💬 Web AI Chat** — BYOK LLM chat panel for natural language queries *(coming soon)*

---

## 📡 Data Sources

| Source | Role | Auth Required |
|--------|------|---------------|
| [ADSB.lol](https://adsb.lol) | Primary — all global flights + military overlay | None |
| [OpenSky Network](https://opensky-network.org) | Supplementary metadata | OAuth2 (optional) |
| [Celestrak](https://celestrak.org) | Satellite TLEs (6 categories) | None |
| [Open-Meteo](https://open-meteo.com) | Weather at aircraft locations | None |
| [CARTO](https://carto.com) | Dark globe tiles | None |

---

## 🚀 Quick Start

### Install

```bash
pip install -e .
```

### Run

```bash
osai serve
```

Open [http://localhost:9096](http://localhost:9096) — works immediately with no API keys.

### Optional: OpenSky OAuth2 (higher rate limits)

Create a `.env` file:

```env
OSAI_OPENSKY_CLIENT_ID=your_client_id
OSAI_OPENSKY_CLIENT_SECRET=your_client_secret
```

### CLI Commands

```bash
osai status    # Show configuration and system status
osai init      # Initialise the database
osai config    # Display current configuration
osai serve     # Start the server
```

---

## 🖥️ Screenshots

*Coming soon*

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────┐
│                  OpenSkyAI                     │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ MCP      │  │ REST API │  │ Web UI       │ │
│  │ Server   │  │ /api/*   │  │ CesiumJS 3D  │ │
│  │ /mcp     │  │          │  │ Globe        │ │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       └──────────────┴───────────────┘         │
│                      │                         │
│         ┌────────────┴─────────────┐           │
│         │   Background Pollers     │           │
│         │   Flights (30s)          │           │
│         │   Satellites (1hr)       │           │
│         └────────────┬─────────────┘           │
│              ┌───────┴────────┐                │
│              │ Service Layer  │                │
│              │ + Classifier   │                │
│              │ + Propagator   │                │
│              └───────┬────────┘                │
│       ┌──────────────┼──────────┐              │
│  ┌────┴─────┐  ┌─────┴────┐  ┌─┴──────────┐  │
│  │ SQLite   │  │ SQLite   │  │ Open-Meteo  │  │
│  │ (flights)│  │ (TLE     │  │ (weather)   │  │
│  │          │  │  cache)  │  │             │  │
│  └────┬─────┘  └─────┬────┘  └─────────────┘  │
│       │               │                        │
│  ┌────┴─────┐  ┌─────┴─────┐                  │
│  │ ADSB.lol │  │ Celestrak │                  │
│  │ + OpenSky│  │           │                  │
│  └──────────┘  └───────────┘                  │
└────────────────────────────────────────────────┘
```

**Design decisions:**
- ADSB.lol is the primary flight source (unfiltered), OpenSky supplements metadata
- All data normalised into a canonical `NormalizedFlight` model before storage
- Frontend uses `BillboardCollection` (not Entity API) for 25k+ aircraft without crashes
- Client-side dead-reckoning interpolation for smooth movement between polls
- Viewport filtering via `computeViewRectangle()` — only visible aircraft rendered
- Satellite altitude exaggerated 15× for visibility on the globe

---

## 📂 Project Structure

```
osai/
├── src/osai/
│   ├── __init__.py
│   ├── cli.py                  # Typer CLI (status, init, serve, config)
│   ├── server.py               # Starlette app + background pollers
│   ├── config.py               # Pydantic Settings (.env)
│   ├── models.py               # NormalizedFlight dataclass
│   ├── flights/
│   │   ├── opensky.py          # OpenSky OAuth2 client
│   │   ├── adsb_lol.py         # ADSB.lol client (primary)
│   │   ├── classifier.py       # Military classifier
│   │   ├── merge.py            # Dual-source merge logic
│   │   └── repository.py       # SQLite flight cache
│   ├── satellites/
│   │   ├── celestrak.py        # TLE fetcher (6 categories)
│   │   ├── propagator.py       # Skyfield/sgp4 propagation
│   │   └── repository.py       # TLE cache
│   ├── weather/
│   │   └── openmeteo.py        # Open-Meteo client
│   ├── storage/
│   │   ├── database.py         # SQLite singleton (WAL mode)
│   │   └── migrations.py       # Versioned schema migrations
│   └── ui/web/
│       ├── index.html          # Globe + toolbar + detail panel
│       ├── flights.js          # Flight rendering + interpolation
│       ├── satellites.js       # Satellite rendering + toggles
│       └── detail.js           # Click panels + fly-to + weather
├── tests/
├── pyproject.toml
├── README.md
├── LICENSE
├── .env.example
└── .gitignore
```

---

## ⚙️ Configuration

All settings via environment variables (prefix `OSAI_`) or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OSAI_HOST` | `0.0.0.0` | Bind host |
| `OSAI_PORT` | `9096` | Bind port |
| `OSAI_DB_PATH` | `~/.osai/osai.db` | SQLite database path |
| `OSAI_OPENSKY_CLIENT_ID` | `None` | OpenSky OAuth2 client ID |
| `OSAI_OPENSKY_CLIENT_SECRET` | `None` | OpenSky OAuth2 secret |
| `OSAI_FLIGHT_POLL_INTERVAL` | `30` | Flight poll interval (seconds) |
| `OSAI_SATELLITE_POLL_INTERVAL` | `3600` | Satellite TLE refresh (seconds) |
| `OSAI_LLM_PROVIDER` | `None` | LiteLLM provider (web chat) |
| `OSAI_LLM_API_KEY` | `None` | LLM API key (web chat) |
| `OSAI_LLM_MODEL` | `None` | LLM model (web chat) |

---

## 🗺️ Roadmap

### v1.0 (In Progress)
- [x] Live flight tracking (dual-source)
- [x] Military aircraft classification
- [x] Satellite tracking (6 categories)
- [x] 3D globe with altitude rendering
- [x] Toggle chips for all categories
- [x] Click detail panels
- [x] Fly-to view + camera history
- [x] Weather overlay
- [ ] MCP tools (8 tools via FastMCP)
- [ ] CLI commands
- [ ] Historical playback
- [ ] Alerts & watch zones
- [ ] Web AI chat (BYOK)
- [ ] PyPI publish

### v2.0+
- ADS-B receiver integration (RTL-SDR)
- Drone tracking (OpenDroneID)
- Ship tracking (AIS)
- Mobile app
- Plugin system

---

## 🔐 Privacy & Security

- All data processing is local
- No user tracking, analytics, or telemetry
- Credentials stored in `.env` (never committed)
- MCP mode: LLM runs in the client — OpenSkyAI never sees conversations

---

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE).
````

**.env.example**

```bash
# OpenSky Network OAuth2 (optional — enables higher rate limits)
# OSAI_OPENSKY_CLIENT_ID=your_client_id
# OSAI_OPENSKY_CLIENT_SECRET=your_client_secret

# Server
# OSAI_HOST=0.0.0.0
# OSAI_PORT=9096

# Poll intervals
# OSAI_FLIGHT_POLL_INTERVAL=30
# OSAI_SATELLITE_POLL_INTERVAL=3600

# LLM (web chat only)
# OSAI_LLM_PROVIDER=
# OSAI_LLM_API_KEY=
# OSAI_LLM_MODEL=
```
