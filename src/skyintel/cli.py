import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="skyintel",
    help="Open Sky Intelligence — real-time flight, military aircraft, and satellite tracking.",
    no_args_is_help=True,
)
console = Console()

def version_callback(value: bool):
    if value:
        from importlib.metadata import version
        console.print(f"skyintel {version('skyintel')}")
        raise typer.Exit()

@app.callback()
def main(version: bool = typer.Option(False, "--version", "-v", callback=version_callback, is_eager=True, help="Show version")):
    pass

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
    table.add_row("Data source", "ADSB.lol (global feed)")
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
        await service.cleanup()

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
        await service.cleanup()

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
        await service.cleanup()

    asyncio.run(_run())

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

@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask the AI"),
    provider: str = typer.Option(None, help="LLM provider (anthropic/openai/google)"),
    api_key: str = typer.Option(None, "--api-key", help="API key"),
    model: str = typer.Option(None, help="Model name"),
):
    """Ask the AI a question using your LLM API key."""
    import asyncio
    from skyintel.config import get_settings
    from skyintel.llm.gateway import chat as llm_chat

    settings = get_settings()
    p = provider or settings.llm_provider
    k = api_key or settings.llm_api_key
    m = model or settings.llm_model

    if not all([p, k, m]):
        console.print("[red]LLM not configured.[/] Set SKYINTEL_LLM_PROVIDER, SKYINTEL_LLM_API_KEY, SKYINTEL_LLM_MODEL in .env or pass --provider, --api-key, --model")
        raise typer.Exit(1)

    async def _run():
        with console.status("[cyan]Thinking…[/]"):
            reply = await llm_chat([{"role": "user", "content": question}], p, k, m, output_format="markdown")
        reply = reply.strip()
        console.print()
        from rich.markdown import Markdown
        console.print(Markdown(reply))
        

    asyncio.run(_run())

@app.command()
def iss(
    passes_flag: bool = typer.Option(False, "--passes", help="Show upcoming pass predictions"),
    lat: float = typer.Option(None, help="Observer latitude (for --passes)"),
    lon: float = typer.Option(None, help="Observer longitude (for --passes)"),
    hours: int = typer.Option(24, help="Lookahead hours (for --passes)"),
):
    """Show ISS position, crew, and pass predictions."""
    import asyncio
    from skyintel import service

    async def _run():
        if passes_flag:
            if lat is None or lon is None:
                console.print("[red]--lat and --lon required for pass predictions[/]")
                return
            result = await service.iss_passes(lat, lon, hours)
            table = Table(title=f"ISS Passes ({result['total_count']})", border_style="dim")
            for col in ["Rise (UTC)", "Direction", "Max Elev", "Set (UTC)", "Duration"]:
                table.add_column(col)
            for p in result["passes"]:
                table.add_row(
                    p.get("rise_utc", "")[:19],
                    p.get("rise_direction", ""),
                    f'{p.get("max_elevation", 0)}°',
                    p.get("set_utc", "")[:19],
                    f'{p.get("duration_seconds", 0)}s',
                )
            console.print(table)
        else:
            pos, crew = await asyncio.gather(service.iss_position(), service.iss_crew())
            table = Table(title="🛰 ISS Status", show_header=False, border_style="dim")
            table.add_column("Key", style="bold cyan")
            table.add_column("Value")
            table.add_row("Latitude", f'{pos.get("latitude", 0):.4f}')
            table.add_row("Longitude", f'{pos.get("longitude", 0):.4f}')
            table.add_row("Altitude", f'{pos.get("altitude_km", 0):.0f} km')
            table.add_row("Speed", f'{pos.get("speed_ms", 0):.0f} m/s')
            table.add_row("Crew", str(crew.get("count", 0)))
            for c in crew.get("crew", []):
                table.add_row("", f' . {c["name"]}')
            console.print(table)
        await service.cleanup()    

    asyncio.run(_run())



