"""CLI commands for engine cycle analysis."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from resa_pro.core.config import DesignState, save_design_json
from resa_pro.cycle.solver import CycleDefinition, CycleType, solve_cycle


@click.group("cycle")
@click.pass_context
def cycle(ctx: click.Context) -> None:
    """Engine cycle analysis commands."""
    pass


@cycle.command("analyze")
@click.option(
    "--type",
    "cycle_type",
    type=click.Choice(["pressure-fed", "gas-generator", "expander"], case_sensitive=False),
    default="pressure-fed",
    show_default=True,
    help="Engine cycle architecture.",
)
@click.option("--thrust", type=float, default=2000.0, show_default=True, help="Design thrust [N].")
@click.option("--pc", type=float, default=2e6, show_default=True, help="Chamber pressure [Pa].")
@click.option("--mr", type=float, default=4.0, show_default=True, help="Mixture ratio (O/F).")
@click.option("--c-star", type=float, default=1550.0, show_default=True, help="Characteristic velocity [m/s].")
@click.option("--gamma", type=float, default=1.21, show_default=True, help="Ratio of specific heats.")
@click.option("--ox-density", type=float, default=1220.0, show_default=True, help="Oxidizer density [kg/m³].")
@click.option("--fuel-density", type=float, default=789.0, show_default=True, help="Fuel density [kg/m³].")
@click.option("--pump-eff", type=float, default=0.65, show_default=True, help="Pump isentropic efficiency.")
@click.option("--turbine-eff", type=float, default=0.60, show_default=True, help="Turbine isentropic efficiency.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def analyze_cmd(
    ctx: click.Context,
    cycle_type: str,
    thrust: float,
    pc: float,
    mr: float,
    c_star: float,
    gamma: float,
    ox_density: float,
    fuel_density: float,
    pump_eff: float,
    turbine_eff: float,
    output: str | None,
) -> None:
    """Analyze an engine cycle architecture."""
    console: Console = ctx.obj.get("console", Console())

    type_map = {
        "pressure-fed": CycleType.PRESSURE_FED,
        "gas-generator": CycleType.GAS_GENERATOR,
        "expander": CycleType.EXPANDER,
    }

    defn = CycleDefinition(
        cycle_type=type_map[cycle_type.lower()],
        chamber_pressure=pc,
        thrust=thrust,
        mixture_ratio=mr,
        c_star=c_star,
        gamma=gamma,
        ox_density=ox_density,
        fuel_density=fuel_density,
        ox_pump_efficiency=pump_eff,
        fuel_pump_efficiency=pump_eff,
        turbine_efficiency=turbine_eff,
    )

    result = solve_cycle(defn)

    console.print(f"\n[bold]RESA Pro — Cycle Analysis ({cycle_type})[/bold]\n")

    # System performance table
    perf_table = Table(title="System Performance")
    perf_table.add_column("Parameter", style="cyan")
    perf_table.add_column("Value", style="green", justify="right")
    perf_table.add_column("Unit", style="dim")

    perf_table.add_row("Cycle Type", result.cycle_type.replace("_", " ").title(), "—")
    perf_table.add_row("Thrust", f"{result.thrust:.0f}", "N")
    perf_table.add_row("Chamber Pressure", f"{result.chamber_pressure / 1e5:.1f}", "bar")
    perf_table.add_row("Total Mass Flow", f"{result.total_mass_flow:.3f}", "kg/s")
    perf_table.add_row("Mixture Ratio (O/F)", f"{result.mixture_ratio:.2f}", "—")
    perf_table.add_row("Isp (delivered)", f"{result.Isp_delivered:.1f}", "s")
    perf_table.add_row("c*", f"{result.c_star:.0f}", "m/s")

    console.print(perf_table)

    # Turbopump table (if applicable)
    if result.pump_power_total > 0 or result.turbine_power_total > 0:
        tp_table = Table(title="Turbopump Power Balance")
        tp_table.add_column("Parameter", style="cyan")
        tp_table.add_column("Value", style="green", justify="right")
        tp_table.add_column("Unit", style="dim")

        tp_table.add_row("Total Pump Power", f"{result.pump_power_total / 1e3:.2f}", "kW")
        tp_table.add_row("Turbine Power", f"{result.turbine_power_total / 1e3:.2f}", "kW")
        tp_table.add_row("Power Balance Error", f"{result.power_balance_error:.1f}", "W")

        console.print(tp_table)

    # Tank pressures
    tank_table = Table(title="Tank Pressures")
    tank_table.add_column("Parameter", style="cyan")
    tank_table.add_column("Value", style="green", justify="right")
    tank_table.add_column("Unit", style="dim")

    tank_table.add_row("Oxidizer Tank", f"{result.tank_pressure_ox / 1e5:.1f}", "bar")
    tank_table.add_row("Fuel Tank", f"{result.tank_pressure_fuel / 1e5:.1f}", "bar")

    console.print(tank_table)

    if output:
        state = DesignState()
        state.performance["cycle"] = {
            "cycle_type": result.cycle_type,
            "thrust": result.thrust,
            "chamber_pressure": result.chamber_pressure,
            "total_mass_flow": result.total_mass_flow,
            "mixture_ratio": result.mixture_ratio,
            "Isp_delivered": result.Isp_delivered,
            "c_star": result.c_star,
            "pump_power_total": result.pump_power_total,
            "turbine_power_total": result.turbine_power_total,
            "power_balance_error": result.power_balance_error,
            "tank_pressure_ox": result.tank_pressure_ox,
            "tank_pressure_fuel": result.tank_pressure_fuel,
        }
        save_design_json(state, output)
        console.print(f"\n[dim]Saved to {output}[/dim]")
