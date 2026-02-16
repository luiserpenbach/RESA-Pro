"""CLI commands for injector design."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from resa_pro.core.config import DesignState, load_design_json, save_design_json
from resa_pro.core.injector import (
    check_chugging_stability,
    design_injector,
)


@click.command("injector")
@click.option(
    "--design",
    type=click.Path(exists=True),
    default=None,
    help="Input design JSON (from chamber command).",
)
@click.option("--mass-flow", type=float, default=None, help="Total mass flow rate [kg/s].")
@click.option("--mr", type=float, default=None, help="Mixture ratio O/F.")
@click.option("--pc", type=float, default=None, help="Chamber pressure [Pa].")
@click.option(
    "--rho-ox",
    type=float,
    default=1220.0,
    show_default=True,
    help="Oxidizer density [kg/m³].",
)
@click.option(
    "--rho-fuel",
    type=float,
    default=789.0,
    show_default=True,
    help="Fuel density [kg/m³].",
)
@click.option(
    "--dp-fraction",
    type=float,
    default=0.20,
    show_default=True,
    help="Injector ΔP as fraction of Pc.",
)
@click.option("--cd-ox", type=float, default=0.65, show_default=True, help="Oxidizer Cd.")
@click.option("--cd-fuel", type=float, default=0.65, show_default=True, help="Fuel Cd.")
@click.option("--n-ox", type=int, default=None, help="Number of oxidizer elements (optional).")
@click.option("--n-fuel", type=int, default=None, help="Number of fuel elements (optional).")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def injector(
    ctx: click.Context,
    design: str | None,
    mass_flow: float | None,
    mr: float | None,
    pc: float | None,
    rho_ox: float,
    rho_fuel: float,
    dp_fraction: float,
    cd_ox: float,
    cd_fuel: float,
    n_ox: int | None,
    n_fuel: int | None,
    output: str | None,
) -> None:
    """Design an injector from mass flow, mixture ratio, and chamber pressure."""
    console: Console = ctx.obj.get("console", Console())

    state: DesignState | None = None
    if design:
        state = load_design_json(design)
        mass_flow = mass_flow or state.chamber.get("mass_flow", 0.0)
        mr = mr or state.mixture_ratio
        pc = pc or state.chamber_pressure

    if not mass_flow or not mr or not pc:
        console.print(
            "[red]Error:[/red] Provide --design or --mass-flow, --mr, and --pc."
        )
        raise SystemExit(1)

    result = design_injector(
        mass_flow=mass_flow,
        mixture_ratio=mr,
        chamber_pressure=pc,
        rho_oxidizer=rho_ox,
        rho_fuel=rho_fuel,
        dp_fraction=dp_fraction,
        cd_ox=cd_ox,
        cd_fuel=cd_fuel,
        n_elements_ox=n_ox,
        n_elements_fuel=n_fuel,
    )

    console.print("\n[bold]RESA Pro — Injector Design[/bold]\n")

    # Oxidizer table
    table_ox = Table(title="Oxidizer Side")
    table_ox.add_column("Parameter", style="cyan")
    table_ox.add_column("Value", style="green", justify="right")
    table_ox.add_column("Unit", style="dim")

    table_ox.add_row("Mass Flow (ox)", f"{result.mass_flow_oxidizer:.4f}", "kg/s")
    table_ox.add_row("Pressure Drop", f"{result.dp_oxidizer / 1e5:.2f}", "bar")
    table_ox.add_row("ΔP/Pc", f"{result.dp_fraction_ox * 100:.1f}", "%")
    table_ox.add_row("Number of Elements", f"{result.n_elements_ox}", "—")
    table_ox.add_row("Orifice Diameter", f"{result.element_ox.diameter * 1e3:.3f}", "mm")
    table_ox.add_row("Injection Velocity", f"{result.element_ox.velocity:.1f}", "m/s")
    table_ox.add_row("Manifold Pressure", f"{result.manifold_pressure_ox / 1e5:.2f}", "bar")

    console.print(table_ox)

    # Fuel table
    table_fuel = Table(title="Fuel Side")
    table_fuel.add_column("Parameter", style="cyan")
    table_fuel.add_column("Value", style="green", justify="right")
    table_fuel.add_column("Unit", style="dim")

    table_fuel.add_row("Mass Flow (fuel)", f"{result.mass_flow_fuel:.4f}", "kg/s")
    table_fuel.add_row("Pressure Drop", f"{result.dp_fuel / 1e5:.2f}", "bar")
    table_fuel.add_row("ΔP/Pc", f"{result.dp_fraction_fuel * 100:.1f}", "%")
    table_fuel.add_row("Number of Elements", f"{result.n_elements_fuel}", "—")
    table_fuel.add_row("Orifice Diameter", f"{result.element_fuel.diameter * 1e3:.3f}", "mm")
    table_fuel.add_row("Injection Velocity", f"{result.element_fuel.velocity:.1f}", "m/s")
    table_fuel.add_row("Manifold Pressure", f"{result.manifold_pressure_fuel / 1e5:.2f}", "bar")

    console.print(table_fuel)

    # Stability check
    stab_ox = check_chugging_stability(result.dp_fraction_ox)
    stab_fuel = check_chugging_stability(result.dp_fraction_fuel)
    status_ox = "[green]STABLE[/green]" if stab_ox["stable"] else "[red]UNSTABLE[/red]"
    status_fuel = "[green]STABLE[/green]" if stab_fuel["stable"] else "[red]UNSTABLE[/red]"

    console.print(f"\nChugging stability:  Ox: {status_ox}  |  Fuel: {status_fuel}")
    console.print(f"Momentum ratio: {result.momentum_ratio:.2f}")

    if output:
        if state is None:
            state = DesignState(
                mixture_ratio=mr,
                chamber_pressure=pc,
            )
        state.feed_system["injector"] = {
            "mass_flow_oxidizer": result.mass_flow_oxidizer,
            "mass_flow_fuel": result.mass_flow_fuel,
            "mixture_ratio": result.mixture_ratio,
            "dp_oxidizer": result.dp_oxidizer,
            "dp_fuel": result.dp_fuel,
            "dp_fraction_ox": result.dp_fraction_ox,
            "dp_fraction_fuel": result.dp_fraction_fuel,
            "n_elements_ox": result.n_elements_ox,
            "element_diameter_ox": result.element_ox.diameter,
            "cd_ox": result.element_ox.cd,
            "n_elements_fuel": result.n_elements_fuel,
            "element_diameter_fuel": result.element_fuel.diameter,
            "cd_fuel": result.element_fuel.cd,
            "manifold_pressure_ox": result.manifold_pressure_ox,
            "manifold_pressure_fuel": result.manifold_pressure_fuel,
            "momentum_ratio": result.momentum_ratio,
        }
        save_design_json(state, output)
        console.print(f"\n[dim]Saved to {output}[/dim]")
