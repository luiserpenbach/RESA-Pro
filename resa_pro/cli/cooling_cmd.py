"""CLI commands for regenerative cooling analysis."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from resa_pro.core.config import DesignState, load_design_json, save_design_json
from resa_pro.core.cooling import analyze_regen_cooling
from resa_pro.core.thermo import lookup_combustion


@click.command("cooling")
@click.option(
    "--design",
    type=click.Path(exists=True),
    required=True,
    help="Input design JSON (must have chamber contour data).",
)
@click.option(
    "--coolant",
    type=click.Choice(["ethanol", "water", "rp1", "methane"], case_sensitive=False),
    default="ethanol",
    show_default=True,
    help="Coolant fluid.",
)
@click.option(
    "--coolant-fraction",
    type=float,
    default=1.0,
    show_default=True,
    help="Fraction of fuel mass flow used as coolant.",
)
@click.option(
    "--coolant-inlet-temp",
    type=float,
    default=293.0,
    show_default=True,
    help="Coolant inlet temperature [K].",
)
@click.option(
    "--channel-width",
    type=float,
    default=1.0,
    show_default=True,
    help="Channel width [mm].",
)
@click.option(
    "--channel-height",
    type=float,
    default=2.0,
    show_default=True,
    help="Channel height [mm].",
)
@click.option(
    "--wall-thickness",
    type=float,
    default=1.0,
    show_default=True,
    help="Inner wall thickness [mm].",
)
@click.option(
    "--wall-material",
    type=click.Choice(["copper", "steel", "inconel"], case_sensitive=False),
    default="copper",
    show_default=True,
    help="Wall material (sets thermal conductivity).",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def cooling(
    ctx: click.Context,
    design: str,
    coolant: str,
    coolant_fraction: float,
    coolant_inlet_temp: float,
    channel_width: float,
    channel_height: float,
    wall_thickness: float,
    wall_material: str,
    output: str | None,
) -> None:
    """Analyze regenerative cooling for a chamber design."""
    console: Console = ctx.obj.get("console", Console())

    state = load_design_json(design)

    # Extract chamber contour
    contour_x = state.chamber.get("contour_x")
    contour_y = state.chamber.get("contour_y")
    if contour_x is None or contour_y is None:
        # Try to re-generate from dimensions
        console.print(
            "[red]Error:[/red] Design file does not contain chamber contour data.\n"
            "Re-run the chamber command with --output to save contour."
        )
        raise SystemExit(1)

    import numpy as np

    contour_x = np.asarray(contour_x)
    contour_y = np.asarray(contour_y)
    throat_radius = state.chamber.get("throat_diameter", 0.0) / 2.0

    if throat_radius <= 0:
        console.print("[red]Error:[/red] Invalid throat diameter in design file.")
        raise SystemExit(1)

    # Lookup combustion data
    try:
        comb = lookup_combustion(state.oxidizer, state.fuel, state.mixture_ratio)
    except KeyError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    # Coolant properties (simplified constant-property values)
    _COOLANT_PROPS = {
        "ethanol": {"cp": 2440.0, "rho": 789.0, "mu": 1.2e-3, "k": 0.17},
        "water": {"cp": 4186.0, "rho": 998.0, "mu": 1.0e-3, "k": 0.60},
        "rp1": {"cp": 2010.0, "rho": 810.0, "mu": 1.6e-3, "k": 0.12},
        "methane": {"cp": 3480.0, "rho": 422.0, "mu": 1.2e-4, "k": 0.19},
    }
    props = _COOLANT_PROPS[coolant.lower()]

    # Wall thermal conductivity
    _WALL_K = {
        "copper": 350.0,
        "steel": 16.0,
        "inconel": 11.4,
    }
    k_wall = _WALL_K[wall_material.lower()]

    # Coolant mass flow = fraction of fuel flow
    mdot = state.chamber.get("mass_flow", 0.0)
    mr = state.mixture_ratio
    mdot_fuel = mdot / (1.0 + mr) if mr > 0 else mdot
    coolant_mdot = coolant_fraction * mdot_fuel

    if coolant_mdot <= 0:
        console.print("[red]Error:[/red] Cannot determine coolant mass flow. Check design file.")
        raise SystemExit(1)

    result = analyze_regen_cooling(
        contour_x=contour_x,
        contour_y=contour_y,
        throat_radius=throat_radius,
        pc=state.chamber_pressure,
        c_star=comb.c_star,
        Tc=comb.chamber_temperature,
        gamma=comb.gamma,
        molar_mass=comb.molar_mass,
        coolant_mass_flow=coolant_mdot,
        coolant_inlet_temp=coolant_inlet_temp,
        coolant_cp=props["cp"],
        coolant_rho=props["rho"],
        coolant_mu=props["mu"],
        coolant_k=props["k"],
        wall_conductivity=k_wall,
        channel_width=channel_width * 1e-3,
        channel_height=channel_height * 1e-3,
        wall_thickness=wall_thickness * 1e-3,
    )

    console.print("\n[bold]RESA Pro — Regenerative Cooling Analysis[/bold]\n")

    table = Table(title="Cooling Summary")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_column("Unit", style="dim")

    table.add_row("Coolant", coolant.capitalize(), "—")
    table.add_row("Wall Material", wall_material.capitalize(), "—")
    table.add_row("Coolant Mass Flow", f"{coolant_mdot:.4f}", "kg/s")
    table.add_row("Coolant Inlet Temp", f"{coolant_inlet_temp:.1f}", "K")
    table.add_row("Coolant Outlet Temp", f"{result.coolant_outlet_temperature:.1f}", "K")
    table.add_row("", "", "")
    table.add_row("Max Wall Temp (gas side)", f"{result.max_wall_temperature:.0f}", "K")
    table.add_row("Max Heat Flux", f"{result.max_heat_flux / 1e6:.2f}", "MW/m²")
    table.add_row("Total Heat Load", f"{result.total_heat_load / 1e3:.2f}", "kW")
    table.add_row("Total Pressure Drop", f"{result.total_pressure_drop / 1e5:.2f}", "bar")
    table.add_row("", "", "")
    table.add_row("Channel Width", f"{channel_width:.1f}", "mm")
    table.add_row("Channel Height", f"{channel_height:.1f}", "mm")
    table.add_row("Wall Thickness", f"{wall_thickness:.1f}", "mm")
    table.add_row("Wall Conductivity", f"{k_wall:.1f}", "W/(m·K)")

    console.print(table)

    # Warning for high wall temperatures
    _MATERIAL_LIMITS = {"copper": 800, "steel": 1100, "inconel": 1250}
    limit = _MATERIAL_LIMITS.get(wall_material.lower(), 1000)
    if result.max_wall_temperature > limit:
        console.print(
            f"\n[red]WARNING:[/red] Peak wall temperature ({result.max_wall_temperature:.0f} K) "
            f"exceeds {wall_material} limit (~{limit} K)."
        )
    else:
        console.print(
            f"\n[green]OK:[/green] Peak wall temperature within {wall_material} limits."
        )

    if output:
        state.cooling = {
            "coolant": coolant,
            "wall_material": wall_material,
            "coolant_mass_flow": coolant_mdot,
            "coolant_inlet_temp": coolant_inlet_temp,
            "coolant_outlet_temp": result.coolant_outlet_temperature,
            "max_wall_temperature": result.max_wall_temperature,
            "max_heat_flux": result.max_heat_flux,
            "total_heat_load": result.total_heat_load,
            "total_pressure_drop": result.total_pressure_drop,
            "channel_width": channel_width * 1e-3,
            "channel_height": channel_height * 1e-3,
            "wall_thickness": wall_thickness * 1e-3,
            "wall_conductivity": k_wall,
        }
        save_design_json(state, output)
        console.print(f"\n[dim]Saved to {output}[/dim]")
