"""CLI commands for feed system sizing."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from resa_pro.core.config import DesignState, load_design_json, save_design_json
from resa_pro.core.feed_system import (
    compute_pressure_budget,
    feed_line_pressure_drop,
    size_pressurant_blowdown,
    size_pressurant_regulated,
    size_tank,
)


@click.group("feed")
@click.pass_context
def feed(ctx: click.Context) -> None:
    """Feed system sizing commands."""
    pass


@feed.command("tank")
@click.option("--mass", type=float, required=True, help="Propellant mass [kg].")
@click.option(
    "--density",
    type=float,
    required=True,
    help="Propellant density [kg/m³].",
)
@click.option("--pressure", type=float, required=True, help="Tank MEOP [Pa].")
@click.option("--diameter", type=float, required=True, help="Tank inner diameter [m].")
@click.option(
    "--yield-strength",
    type=float,
    default=276e6,
    show_default=True,
    help="Material yield strength [Pa] (default: Al 6061-T6).",
)
@click.option(
    "--mat-density",
    type=float,
    default=2700.0,
    show_default=True,
    help="Material density [kg/m³].",
)
@click.option(
    "--safety-factor",
    type=float,
    default=2.0,
    show_default=True,
    help="Structural safety factor.",
)
@click.option(
    "--ullage",
    type=float,
    default=0.05,
    show_default=True,
    help="Ullage volume fraction.",
)
@click.option("--name", type=str, default="", help="Propellant name (for labelling).")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def tank_cmd(
    ctx: click.Context,
    mass: float,
    density: float,
    pressure: float,
    diameter: float,
    yield_strength: float,
    mat_density: float,
    safety_factor: float,
    ullage: float,
    name: str,
    output: str | None,
) -> None:
    """Size a propellant tank."""
    console: Console = ctx.obj.get("console", Console())

    result = size_tank(
        propellant_mass=mass,
        propellant_density=density,
        tank_pressure=pressure,
        inner_diameter=diameter,
        material_yield_strength=yield_strength,
        material_density=mat_density,
        safety_factor=safety_factor,
        ullage_fraction=ullage,
        propellant_name=name,
    )

    console.print("\n[bold]RESA Pro — Tank Sizing[/bold]\n")

    table = Table(title="Tank Design")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_column("Unit", style="dim")

    if name:
        table.add_row("Propellant", name, "—")
    table.add_row("Propellant Mass", f"{mass:.2f}", "kg")
    table.add_row("Propellant Volume", f"{result.propellant_volume * 1e3:.2f}", "L")
    table.add_row("Total Volume", f"{result.total_volume * 1e3:.2f}", "L")
    table.add_row("Tank MEOP", f"{pressure / 1e5:.1f}", "bar")
    table.add_row("Inner Diameter", f"{diameter * 1e3:.1f}", "mm")
    table.add_row("Cylinder Length", f"{result.cylinder_length * 1e3:.1f}", "mm")
    table.add_row("Wall Thickness", f"{result.wall_thickness * 1e3:.2f}", "mm")
    table.add_row("Tank Mass (structure)", f"{result.tank_mass:.3f}", "kg")

    console.print(table)

    if output:
        state = DesignState()
        state.feed_system["tank"] = {
            "propellant": name,
            "propellant_mass": mass,
            "propellant_volume": result.propellant_volume,
            "total_volume": result.total_volume,
            "tank_pressure": pressure,
            "inner_diameter": diameter,
            "cylinder_length": result.cylinder_length,
            "wall_thickness": result.wall_thickness,
            "tank_mass": result.tank_mass,
        }
        save_design_json(state, output)
        console.print(f"\n[dim]Saved to {output}[/dim]")


@feed.command("pressurant")
@click.option("--tank-volume", type=float, required=True, help="Tank volume to pressurise [L].")
@click.option("--tank-pressure", type=float, required=True, help="Required tank pressure [Pa].")
@click.option(
    "--mode",
    type=click.Choice(["blowdown", "regulated"], case_sensitive=False),
    default="blowdown",
    show_default=True,
    help="Pressurisation mode.",
)
@click.option(
    "--blowdown-ratio",
    type=float,
    default=3.0,
    show_default=True,
    help="Blowdown ratio P_initial/P_final (blowdown mode).",
)
@click.option(
    "--bottle-pressure",
    type=float,
    default=300e5,
    show_default=True,
    help="Initial bottle pressure [Pa] (regulated mode).",
)
@click.option(
    "--gas",
    type=click.Choice(["nitrogen", "helium"], case_sensitive=False),
    default="nitrogen",
    show_default=True,
    help="Pressurant gas.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def pressurant_cmd(
    ctx: click.Context,
    tank_volume: float,
    tank_pressure: float,
    mode: str,
    blowdown_ratio: float,
    bottle_pressure: float,
    gas: str,
    output: str | None,
) -> None:
    """Size the pressurisation system."""
    console: Console = ctx.obj.get("console", Console())

    # Convert litres to m³
    V = tank_volume * 1e-3

    _GAS_PROPS = {
        "nitrogen": {"gamma": 1.4, "M": 0.028},
        "helium": {"gamma": 1.667, "M": 0.004},
    }
    gp = _GAS_PROPS[gas.lower()]

    if mode.lower() == "blowdown":
        result = size_pressurant_blowdown(
            tank_volume=V,
            tank_pressure=tank_pressure,
            pressurant_gamma=gp["gamma"],
            pressurant_molar_mass=gp["M"],
            blowdown_ratio=blowdown_ratio,
            gas_name=gas,
        )
    else:
        result = size_pressurant_regulated(
            tank_volume=V,
            regulated_pressure=tank_pressure,
            bottle_pressure=bottle_pressure,
            pressurant_molar_mass=gp["M"],
            gas_name=gas,
        )

    console.print(f"\n[bold]RESA Pro — Pressurant Sizing ({mode})[/bold]\n")

    table = Table(title="Pressurant System")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_column("Unit", style="dim")

    table.add_row("Gas", gas.capitalize(), "—")
    table.add_row("Mode", mode.capitalize(), "—")
    table.add_row("Pressurant Mass", f"{result.pressurant_mass:.3f}", "kg")
    table.add_row("Bottle Volume", f"{result.bottle_volume * 1e3:.2f}", "L")
    table.add_row("Initial Pressure", f"{result.bottle_pressure_initial / 1e5:.1f}", "bar")
    table.add_row("Final Pressure", f"{result.bottle_pressure_final / 1e5:.1f}", "bar")
    table.add_row("Blowdown Ratio", f"{result.blowdown_ratio:.1f}", "—")

    console.print(table)

    if output:
        state = DesignState()
        state.feed_system["pressurant"] = {
            "gas": gas,
            "mode": mode,
            "pressurant_mass": result.pressurant_mass,
            "bottle_volume": result.bottle_volume,
            "bottle_pressure_initial": result.bottle_pressure_initial,
            "bottle_pressure_final": result.bottle_pressure_final,
            "blowdown_ratio": result.blowdown_ratio,
        }
        save_design_json(state, output)
        console.print(f"\n[dim]Saved to {output}[/dim]")


@feed.command("budget")
@click.option("--pc", type=float, required=True, help="Chamber pressure [Pa].")
@click.option("--injector-dp", type=float, required=True, help="Injector ΔP [Pa].")
@click.option("--feed-line-dp", type=float, default=0.0, help="Feed line ΔP [Pa].")
@click.option("--cooling-dp", type=float, default=0.0, help="Cooling jacket ΔP [Pa].")
@click.option(
    "--valve-dp",
    type=float,
    default=50000.0,
    show_default=True,
    help="Valve ΔP [Pa].",
)
@click.option(
    "--margin",
    type=float,
    default=0.10,
    show_default=True,
    help="Pressure margin fraction.",
)
@click.pass_context
def budget_cmd(
    ctx: click.Context,
    pc: float,
    injector_dp: float,
    feed_line_dp: float,
    cooling_dp: float,
    valve_dp: float,
    margin: float,
) -> None:
    """Compute the system pressure budget."""
    console: Console = ctx.obj.get("console", Console())

    result = compute_pressure_budget(
        chamber_pressure=pc,
        injector_dp=injector_dp,
        feed_line_dp=feed_line_dp,
        cooling_dp=cooling_dp,
        valve_dp=valve_dp,
        margin_fraction=margin,
    )

    console.print("\n[bold]RESA Pro — Pressure Budget[/bold]\n")

    table = Table(title="Pressure Budget")
    table.add_column("Item", style="cyan")
    table.add_column("Pressure", style="green", justify="right")
    table.add_column("Unit", style="dim")

    table.add_row("Chamber Pressure", f"{pc / 1e5:.1f}", "bar")
    table.add_row("Injector ΔP", f"{injector_dp / 1e5:.2f}", "bar")
    table.add_row("Feed Line ΔP", f"{feed_line_dp / 1e5:.2f}", "bar")
    table.add_row("Cooling ΔP", f"{cooling_dp / 1e5:.2f}", "bar")
    table.add_row("Valve ΔP", f"{valve_dp / 1e5:.2f}", "bar")
    table.add_row("Margin", f"{result.margin / 1e5:.2f}", "bar")
    table.add_row("", "", "")
    table.add_row("[bold]Required Tank Pressure[/bold]", f"[bold]{result.required_tank_pressure / 1e5:.1f}[/bold]", "bar")

    console.print(table)
