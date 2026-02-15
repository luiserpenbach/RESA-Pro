"""CLI command for inspecting design files and listing propellants/materials."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from resa_pro.core.config import load_design_json
from resa_pro.core.fluids import list_propellants, get_propellant_info
from resa_pro.core.materials import list_materials, get_material_info


@click.group("info")
@click.pass_context
def info(ctx: click.Context) -> None:
    """Inspect design files, propellants, and materials."""
    pass


@info.command("design")
@click.argument("path", type=click.Path(exists=True))
@click.pass_context
def info_design(ctx: click.Context, path: str) -> None:
    """Display summary of a design file."""
    console: Console = ctx.obj.get("console", Console())
    state = load_design_json(path)

    tree = Tree(f"[bold]{state.meta.name}[/bold]")
    meta = tree.add("[cyan]Metadata[/cyan]")
    meta.add(f"Author: {state.meta.author or '—'}")
    meta.add(f"Version: {state.meta.version}")
    meta.add(f"Modified: {state.meta.modified or '—'}")

    op = tree.add("[cyan]Operating Point[/cyan]")
    op.add(f"Oxidizer: {state.oxidizer}")
    op.add(f"Fuel: {state.fuel}")
    op.add(f"Mixture Ratio: {state.mixture_ratio}")
    op.add(f"Chamber Pressure: {state.chamber_pressure / 1e5:.1f} bar")
    op.add(f"Thrust: {state.thrust:.0f} N")

    if state.chamber:
        ch = tree.add("[cyan]Chamber[/cyan]")
        for k, v in state.chamber.items():
            if k.startswith("contour"):
                continue  # skip arrays
            ch.add(f"{k}: {v}")

    if state.nozzle:
        nz = tree.add("[cyan]Nozzle[/cyan]")
        for k, v in state.nozzle.items():
            if k.startswith("contour"):
                continue
            nz.add(f"{k}: {v}")

    if state.performance:
        perf = tree.add("[cyan]Performance[/cyan]")
        for k, v in state.performance.items():
            perf.add(f"{k}: {v}")

    console.print(tree)


@info.command("propellants")
@click.pass_context
def info_propellants(ctx: click.Context) -> None:
    """List available propellants."""
    console: Console = ctx.obj.get("console", Console())
    table = Table(title="Available Propellants")
    table.add_column("Name", style="cyan")
    table.add_column("Formula", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("CoolProp Name", style="dim")

    for name in list_propellants():
        info = get_propellant_info(name)
        table.add_row(
            name,
            info.get("formula", "—"),
            info.get("type", "—"),
            info.get("coolprop_name", "—"),
        )
    console.print(table)


@info.command("materials")
@click.pass_context
def info_materials(ctx: click.Context) -> None:
    """List available materials."""
    console: Console = ctx.obj.get("console", Console())
    table = Table(title="Available Materials")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Density [kg/m³]", justify="right")
    table.add_column("Melting Pt [K]", justify="right")

    for mat_id in list_materials():
        info = get_material_info(mat_id)
        table.add_row(
            mat_id,
            info["name"],
            info["category"],
            str(info["density"]),
            str(info["melting_point"]),
        )
    console.print(table)
