import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="osai",
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
        console.print("[bold yellow]MCP stdio mode — coming in Phase 12[/]")
        return

    settings = get_settings()
    bind_host = host or settings.host
    bind_port = port or settings.port

    console.print(f"[bold green]🔭 OpenSkyAI[/] starting at [bold]http://{bind_host}:{bind_port}[/]")
    uvicorn.run("osai.server:app", host=bind_host, port=bind_port, log_level="info")


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
