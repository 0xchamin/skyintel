import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="skyintel",
    help="OpenSkyAI — real-time flight, military aircraft, and satellite tracking.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def status():
    """Show OpenSkyAI configuration and system status."""
    from skyintel.config import get_settings

    settings = get_settings()

    table = Table(title="OpenSkyAI Status", show_header=False, border_style="dim")
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    table.add_row("Host", settings.host)
    table.add_row("Port", str(settings.port))
    table.add_row("Database", str(settings.db_path))
    table.add_row("DB exists", "✓" if settings.db_path.exists() else "✗")
    table.add_row("OpenSky OAuth2", "✓ configured" if settings.opensky_configured else "✗ not set")
    table.add_row("Flight poll", f"{settings.flight_poll_interval}s")
    table.add_row("Satellite poll", f"{settings.satellite_poll_interval}s")
    table.add_row("LLM", f"{settings.llm_provider} / {settings.llm_model}" if settings.llm_configured else "✗ not set")

    console.print()
    console.print(table)
    console.print()


@app.command()
def serve(
    host: str = typer.Option(None, help="Bind host (overrides .env)"),
    port: int = typer.Option(None, help="Bind port (overrides .env)"),
    stdio: bool = typer.Option(False, "--stdio", help="Run as MCP stdio server for Claude Desktop / VS Code"),
):
    """Start the OpenSkyAI server (MCP + REST + Web UI)."""
    import uvicorn
    import logging
    from skyintel.config import get_settings

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    if stdio:
        from skyintel.mcp_tools import mcp
        mcp.run(transport="stdio")
        return


    settings = get_settings()
    bind_host = host or settings.host
    bind_port = port or settings.port

    console.print(f"[bold green]🔭 OpenSkyAI[/] starting at [bold]http://{bind_host}:{bind_port}[/]")
    #uvicorn.run("osai.server:app", host=bind_host, port=bind_port, log_level="info")
    uvicorn.run("skyintel.server:app", host=bind_host, port=bind_port, log_level="info")



@app.command()
def init():
    """Initialise the database (creates ~/.osai/osai.db)."""
    import asyncio
    from skyintel.config import get_settings
    from skyintel.storage.database import get_db, close_db
    from skyintel.storage.migrations import run_migrations

    async def _init():
        settings = get_settings()
        db = await get_db(settings.db_path)
        await run_migrations(db)
        await close_db()
        console.print(f"[green]✓[/] Database initialised at [bold]{settings.db_path}[/]")

    asyncio.run(_init())


@app.command()
def config():
    """Open or display the current .env configuration."""
    from skyintel.config import get_settings

    settings = get_settings()
    console.print(settings.model_dump_json(indent=2))

@app.command()
def flights(
    lat: float = typer.Option(None, help="Latitude"),
    lon: float = typer.Option(None, help="Longitude"),
    radius: float = typer.Option(100, help="Radius in km"),
    military_only: bool = typer.Option(False, "--military", help="Military flights only"),
    query: str = typer.Option(None, "--search", help="Search by callsign or ICAO24"),
):
    """List live flights — nearby, military, or search."""
    import asyncio
    from skyintel import service

    async def _run():
        if query:
            results = await service.search_flight(query)
        elif military_only:
            results = await service.military_flights()
        elif lat is not None and lon is not None:
            results = await service.flights_near(lat, lon, radius)
        else:
            console.print("[red]Provide --search, --military, or --lat/--lon[/]")
            return

        table = Table(title=f"Flights ({len(results)})", border_style="dim")
        for col in ["ICAO24", "Callsign", "Type", "Alt (ft)", "Speed (kt)", "Heading"]:
            table.add_column(col)
        for f in results:
            alt = str(round(f["altitude_m"] * 3.28084)) if f.get("altitude_m") else ""
            spd = str(round(f["velocity_ms"] * 1.94384)) if f.get("velocity_ms") else ""
            hdg = str(round(f["heading"])) + "°" if f.get("heading") else ""
            table.add_row(f["icao24"], f.get("callsign") or "", f.get("aircraft_type", ""), alt, spd, hdg)
        console.print(table)

    asyncio.run(_run())

@app.command()
def satellites(
    category: str = typer.Option(None, help="Filter by category (iss, military, weather, nav, science, starlink)"),
):
    """List current satellite positions."""
    import asyncio
    from skyintel import service

    async def _run():
        results = await service.get_satellites(category)
        table = Table(title=f"Satellites ({len(results)})", border_style="dim")
        for col in ["NORAD", "Name", "Category", "Alt (km)", "Speed (m/s)", "Lat", "Lon"]:
            table.add_column(col)
        for s in results:
            table.add_row(
                str(s["norad_id"]), s["name"], s["category"],
                str(round(s.get("altitude_km", 0))),
                str(round(s.get("speed_ms", 0))),
                f'{s["latitude"]:.2f}', f'{s["longitude"]:.2f}',
            )
        console.print(table)

    asyncio.run(_run())

@app.command()
def above(
    lat: float = typer.Option(..., help="Latitude"),
    lon: float = typer.Option(..., help="Longitude"),
    radius: float = typer.Option(100, help="Radius in km"),
):
    """Show flights and satellites above a location."""
    import asyncio
    from skyintel import service

    async def _run():
        flights_data, sats_data = await asyncio.gather(
            service.flights_near(lat, lon, radius),
            service.get_satellites(),
        )

        # Filter satellites by rough distance
        import math
        # nearby_sats = []
        # for s in sats_data:
        #     dlat = s["latitude"] - lat
        #     dlon = s["longitude"] - lon
        #     dist_km = math.sqrt(dlat**2 + dlon**2) * 111
        #     if dist_km <= radius:
        #         nearby_sats.append(s)

        nearby_sats = []
        for s in sats_data:
            dlat = math.radians(s["latitude"] - lat)
            dlon = math.radians(s["longitude"] - lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(s["latitude"])) * math.sin(dlon/2)**2
            dist_km = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            if dist_km <= radius:
                nearby_sats.append(s)


        console.print(f"\n[bold cyan]📍 Above ({lat:.2f}, {lon:.2f}) — {radius}km radius[/]\n")

        ft = Table(title=f"Flights ({len(flights_data)})", border_style="dim")
        for col in ["ICAO24", "Callsign", "Type", "Alt (ft)", "Speed (kt)"]:
            ft.add_column(col)
        for f in flights_data:
            alt = str(round(f["altitude_m"] * 3.28084)) if f.get("altitude_m") else ""
            spd = str(round(f["velocity_ms"] * 1.94384)) if f.get("velocity_ms") else ""
            ft.add_row(f["icao24"], f.get("callsign") or "", f.get("aircraft_type", ""), alt, spd)
        console.print(ft)

        st = Table(title=f"Satellites ({len(nearby_sats)})", border_style="dim")
        for col in ["NORAD", "Name", "Category", "Alt (km)"]:
            st.add_column(col)
        for s in nearby_sats:
            st.add_row(str(s["norad_id"]), s["name"], s["category"], str(round(s.get("altitude_km", 0))))
        console.print(st)

    asyncio.run(_run())


# @app.command(name="mcp-config")
# def mcp_config(
#     stdio: bool = typer.Option(False, "--stdio", help="Print stdio config instead of HTTP"),
# ):
#     """Print MCP configuration snippet for Claude Desktop / Cursor."""
#     import json
#     from skyintel.config import get_settings
#     if stdio:
#         config = {"mcpServers": {"skyintel": {"command": "skyintel", "args": ["serve", "--stdio"]}}}
#     else:
#         settings = get_settings()
#         config = {"mcpServers": {"skyintel": {"url": f"http://localhost:{settings.port}/mcp"}}}
#     console.print("\n[bold cyan]Add this to your mcp.json:[/]\n")
#     console.print(json.dumps(config, indent=2))
#     console.print()

@app.command(name="mcp-config")
def mcp_config(
    stdio: bool = typer.Option(False, "--stdio", help="Print stdio config"),
    vscode: bool = typer.Option(False, "--vscode", help="Print VS Code format"),
):
    """Print MCP configuration snippet for Claude Desktop / VS Code / Cursor."""
    import json
    from skyintel.config import get_settings

    if stdio:
        inner = {"command": "skyintel", "args": ["serve", "--stdio"]}
    else:
        settings = get_settings()
        inner = {"url": f"http://localhost:{settings.port}/mcp"}

    key = "servers" if vscode else "mcpServers"
    config = {key: {"skyintel": inner}}

    target = "VS Code" if vscode else "Claude Desktop / Cursor"
    console.print(f"\n[bold cyan]Add this to your mcp.json ({target}):[/]\n")
    console.print(json.dumps(config, indent=2))
    console.print()

