"""
Megazord CLI
Command-line interface for cluster management
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

from megazord import __version__
from megazord.core.params import Params
from megazord.core.hash import H, M
from megazord.core.states import ST
from megazord.megazord import Megazord

app = typer.Typer(
    name="megazord",
    help="Generic Local LLM Cluster - ISA-88/95/101 Compliant",
    add_completion=False,
)

console = Console()

# Subcommand groups
gpu_app = typer.Typer(help="GPU management commands")
model_app = typer.Typer(help="Model management commands")
config_app = typer.Typer(help="Configuration commands")

app.add_typer(gpu_app, name="gpu")
app.add_typer(model_app, name="model")
app.add_typer(config_app, name="config")


def get_megazord(db_path: str | None = None) -> Megazord:
    """Get or create Megazord instance."""
    return Megazord(db_path=db_path)


async def async_init(z: Megazord) -> bool:
    """Async initialization helper."""
    return await z.init()


# --- Main Commands ---

@app.command()
def version():
    """Show version information."""
    rprint(f"[bold cyan]Megazord[/] v{__version__}")
    rprint("[dim]Generic Local LLM Cluster - ISA-88/95/101 Compliant[/]")


@app.command()
def init(
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Initialize Megazord database and scan GPUs."""
    z = get_megazord(db_path)
    success = asyncio.run(async_init(z))

    if not success:
        rprint("[red]Initialization failed[/]")
        raise typer.Exit(1)

    # Scan GPUs
    gpus = z.scan()

    rprint(f"[green]Initialized Megazord[/]")
    rprint(f"  Database: {z.params.sys.db_path_resolved}")
    rprint(f"  GPUs detected: {len(gpus)}")

    if gpus:
        table = Table(title="GPUs")
        table.add_column("Idx", style="cyan")
        table.add_column("Name")
        table.add_column("VRAM (GB)", justify="right")
        table.add_column("Temp", justify="right")
        table.add_column("Status")

        for gpu in gpus:
            status_color = "green" if gpu.ok else "yellow" if gpu.status == ST.THROTTLE else "red"
            table.add_row(
                str(gpu.idx),
                gpu.name,
                f"{gpu.vram_total / 1024:.1f}",
                f"{gpu.temp}°C",
                f"[{status_color}]{ST(gpu.status).label}[/]",
            )

        console.print(table)


@app.command()
def status(
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Show cluster status."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))
    z.scan()

    stats = z.router.stats
    vram = z.router.get_vram_summary()
    temp = z.router.get_temp_summary()

    # Main status panel
    panel = Panel(
        f"""[bold]{z.params.sys.name}[/]

[cyan]GPUs:[/]     {stats['gpu_count']} total, {stats['gpu_ready']} ready
[cyan]VRAM:[/]     {vram['available_mb'] / 1024:.1f} / {vram['total_mb'] / 1024:.1f} GB available
[cyan]Temp:[/]     Max {temp['max']}°C, Avg {temp['avg']:.1f}°C

[cyan]Models:[/]   {stats['model_count']} registered, {stats['model_loaded']} loaded
[cyan]Queue:[/]    {stats['queue_depth']} pending
[cyan]Router:[/]   {stats['state']}
""",
        title="Megazord Status",
        border_style="cyan",
    )
    console.print(panel)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8420, "--port", "-p", help="Bind port"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Start the API server."""
    z = get_megazord(db_path)

    rprint(f"[bold cyan]Starting Megazord API server...[/]")
    rprint(f"  Host: {host}")
    rprint(f"  Port: {port}")
    rprint(f"  Docs: http://{host}:{port}/docs")

    asyncio.run(z.serve(host=host, port=port))


# --- GPU Commands ---

@gpu_app.command("ls")
def gpu_list(
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """List all GPUs."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))
    gpus = z.scan()

    if not gpus:
        rprint("[yellow]No GPUs detected[/]")
        return

    table = Table(title="GPUs")
    table.add_column("Hash", style="dim")
    table.add_column("Idx", style="cyan")
    table.add_column("Name")
    table.add_column("VRAM Total", justify="right")
    table.add_column("VRAM Avail", justify="right")
    table.add_column("Speed", justify="right")
    table.add_column("Temp", justify="right")
    table.add_column("Load", justify="right")
    table.add_column("Status")

    for gpu in gpus:
        status_color = "green" if gpu.ok else "yellow" if gpu.status == ST.THROTTLE else "red"
        table.add_row(
            gpu.h,
            str(gpu.idx),
            gpu.name,
            f"{gpu.vram_total / 1024:.1f} GB",
            f"{gpu.vram_avail / 1024:.1f} GB",
            f"{gpu.speed:.1f} t/s" if gpu.speed else "-",
            f"{gpu.temp}°C",
            f"{gpu.load * 100:.0f}%",
            f"[{status_color}]{ST(gpu.status).label}[/]",
        )

    console.print(table)


@gpu_app.command("add")
def gpu_add(
    indices: list[int] = typer.Argument(..., help="GPU indices to add"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Add GPUs by index."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))

    for idx in indices:
        gpu = z.g(idx)
        if gpu:
            rprint(f"[green]Added GPU {idx}:[/] {gpu.name}")
        else:
            rprint(f"[red]Failed to add GPU {idx}[/]")


@gpu_app.command("rm")
def gpu_remove(
    indices: list[int] = typer.Argument(..., help="GPU indices to remove"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Remove GPUs by index."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))

    for idx in indices:
        for gpu in z.router.gpus:
            if gpu.idx == idx:
                z.router.unregister_gpu(gpu.h)
                rprint(f"[yellow]Removed GPU {idx}[/]")
                break


@gpu_app.command("bench")
def gpu_benchmark(
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Benchmark all GPUs."""
    rprint("[yellow]GPU benchmarking not yet implemented[/]")
    rprint("[dim]Coming soon: token/s measurement per GPU[/]")


# --- Model Commands ---

@model_app.command("ls")
def model_list(
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """List all models."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))

    models = z.router.models

    if not models:
        rprint("[yellow]No models registered[/]")
        return

    table = Table(title="Models")
    table.add_column("Hash", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("VRAM", justify="right")
    table.add_column("Shard")
    table.add_column("Status")
    table.add_column("GPUs")

    for model in models:
        status = "[green]Loaded[/]" if model.loaded else "[dim]Unloaded[/]"
        gpus = ", ".join(model.on) if model.on else "-"
        table.add_row(
            model.h,
            model.name,
            f"{model.vram / 1024:.1f} GB",
            "Yes" if model.shard else "No",
            status,
            gpus,
        )

    console.print(table)


@model_app.command("add")
def model_add(
    name: str = typer.Argument(..., help="Model name"),
    vram: int = typer.Argument(..., help="VRAM required (MB)"),
    shard: bool = typer.Option(True, "--shard/--no-shard", help="Allow sharding"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Register a new model."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))

    async def add():
        return await z.add_model(name=name, vram=vram, shard=shard)

    model = asyncio.run(add())
    rprint(f"[green]Model registered:[/] {model.name} ({model.h})")


@model_app.command("load")
def model_load(
    name: str = typer.Argument(..., help="Model name"),
    gpus: Optional[list[int]] = typer.Option(None, "--gpu", "-g", help="Specific GPU indices"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Load a model onto GPU(s)."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))
    z.scan()

    model = z.router.get_model_by_name(name)
    if not model:
        rprint(f"[red]Model not found:[/] {name}")
        raise typer.Exit(1)

    async def load():
        return await z.load_model(model.h, gpus)

    success = asyncio.run(load())

    if success:
        model = z.router.get_model(model.h)
        rprint(f"[green]Model loaded:[/] {name} on GPUs {model.on}")
    else:
        rprint(f"[red]Failed to load model:[/] {name}")
        raise typer.Exit(1)


@model_app.command("unload")
def model_unload(
    name: str = typer.Argument(..., help="Model name"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Unload a model from GPU(s)."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))

    model = z.router.get_model_by_name(name)
    if not model:
        rprint(f"[red]Model not found:[/] {name}")
        raise typer.Exit(1)

    async def unload():
        return await z.unload_model(model.h)

    success = asyncio.run(unload())

    if success:
        rprint(f"[green]Model unloaded:[/] {name}")
    else:
        rprint(f"[red]Failed to unload model:[/] {name}")
        raise typer.Exit(1)


# --- Config Commands ---

@config_app.command("get")
def config_get(
    key: Optional[str] = typer.Argument(None, help="Config key (omit for all)"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Get configuration value(s)."""
    z = get_megazord(db_path)

    params = z.params.to_dict()

    if key:
        # Navigate nested keys
        parts = key.split(".")
        value = params
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                rprint(f"[red]Key not found:[/] {key}")
                raise typer.Exit(1)
        rprint(f"{key} = {json.dumps(value)}")
    else:
        rprint(json.dumps(params, indent=2))


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="Config value"),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path"),
):
    """Set configuration value."""
    z = get_megazord(db_path)
    asyncio.run(async_init(z))

    # Parse value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value

    async def set_param():
        if z.db:
            await z.db.set_param(key, parsed)

    asyncio.run(set_param())
    rprint(f"[green]Set[/] {key} = {parsed}")


def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
