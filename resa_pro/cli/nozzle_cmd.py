"""CLI commands for nozzle design."""

from __future__ import annotations

import json
from pathlib import Path

import click
import numpy as np
from rich.console import Console
from rich.table import Table

from resa_pro.core.config import DesignState, load_design_json, save_design_json
from resa_pro.core.nozzle import (
    NozzleMethod,
    conical_nozzle,
    compute_nozzle_efficiency,
    parabolic_nozzle,
)
from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion
from resa_pro.utils.constants import RAD_TO_DEG


@click.command("nozzle")
@click.option(
    "--method",
    type=click.Choice(["conical", "parabolic"], case_sensitive=False),
    default="parabolic",
    show_default=True,
    help="Nozzle contour method.",
)
@click.option("--expansion-ratio", "-e", type=float, required=True, help="Ae/At.")
@click.option(
    "--design",
    type=click.Path(exists=True),
    default=None,
    help="Input design JSON (from chamber command).",
)
@click.option(
    "--throat-radius", type=float, default=None, help="Throat radius [m] (if no design file)."
)
@click.option(
    "--half-angle", type=float, default=15.0, show_default=True, help="Conical half-angle [deg]."
)
@click.option(
    "--frac-length",
    type=float,
    default=0.8,
    show_default=True,
    help="Parabolic fractional length (0.6–0.9).",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def nozzle(
    ctx: click.Context,
    method: str,
    expansion_ratio: float,
    design: str | None,
    throat_radius: float | None,
    half_angle: float,
    frac_length: float,
    output: str | None,
) -> None:
    """Design a nozzle contour and compute performance."""
    console: Console = ctx.obj.get("console", Console())

    # Load throat radius from design file or CLI
    state: DesignState | None = None
    if design:
        state = load_design_json(design)
        Rt = state.chamber.get("throat_diameter", 0) / 2.0
        if Rt <= 0:
            console.print("[red]Error:[/red] Design file missing throat_diameter.")
            raise SystemExit(1)
    elif throat_radius is not None:
        Rt = throat_radius
    else:
        console.print("[red]Error:[/red] Provide --design or --throat-radius.")
        raise SystemExit(1)

    # Generate contour
    if method.lower() == "conical":
        contour = conical_nozzle(Rt, expansion_ratio, half_angle=half_angle)
    else:
        contour = parabolic_nozzle(Rt, expansion_ratio, fractional_length=frac_length)

    console.print(f"\n[bold]RESA Pro — Nozzle Design ({method})[/bold]\n")

    # Performance (if we have propellant info)
    perf = None
    if state and state.chamber_pressure > 0:
        try:
            comb = lookup_combustion(state.oxidizer, state.fuel, state.mixture_ratio)
            perf = compute_nozzle_performance(
                gamma=comb.gamma,
                molar_mass=comb.molar_mass,
                Tc=comb.chamber_temperature,
                expansion_ratio=expansion_ratio,
                pc=state.chamber_pressure,
            )
        except KeyError:
            pass

    # Display results
    table = Table(title="Nozzle Design Results")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_column("Unit", style="dim")

    table.add_row("Method", method.capitalize(), "—")
    table.add_row("Expansion Ratio", f"{expansion_ratio:.1f}", "—")
    table.add_row("Throat Radius", f"{Rt * 1e3:.2f}", "mm")
    table.add_row("Exit Radius", f"{contour.exit_radius * 1e3:.2f}", "mm")
    table.add_row("Nozzle Length", f"{contour.length * 1e3:.2f}", "mm")
    table.add_row("Divergence Efficiency", f"{contour.divergence_efficiency:.4f}", "—")

    if method.lower() == "conical":
        table.add_row("Half-Angle", f"{contour.half_angle * RAD_TO_DEG:.1f}", "deg")
    else:
        table.add_row("θ Initial", f"{contour.theta_initial * RAD_TO_DEG:.1f}", "deg")
        table.add_row("θ Exit", f"{contour.theta_exit * RAD_TO_DEG:.1f}", "deg")

    if perf:
        table.add_row("", "", "")
        table.add_row("[bold]Performance[/bold]", "", "")
        table.add_row("c*", f"{perf.c_star:.1f}", "m/s")
        table.add_row("CF (vacuum)", f"{perf.CF_vac:.4f}", "—")
        table.add_row("CF (sea level)", f"{perf.CF_sl:.4f}", "—")
        table.add_row("Isp (vacuum)", f"{perf.Isp_vac:.1f}", "s")
        table.add_row("Isp (sea level)", f"{perf.Isp_sl:.1f}", "s")
        table.add_row("Exit Mach", f"{perf.exit_mach:.2f}", "—")

    console.print(table)

    # Save
    if output:
        if state is None:
            state = DesignState()
        state.nozzle = {
            "method": method,
            "expansion_ratio": expansion_ratio,
            "throat_radius": Rt,
            "exit_radius": contour.exit_radius,
            "length": contour.length,
            "divergence_efficiency": contour.divergence_efficiency,
            "contour_x": contour.x.tolist(),
            "contour_y": contour.y.tolist(),
        }
        if perf:
            state.performance = {
                "c_star": perf.c_star,
                "CF_vac": perf.CF_vac,
                "CF_sl": perf.CF_sl,
                "Isp_vac": perf.Isp_vac,
                "Isp_sl": perf.Isp_sl,
                "exit_mach": perf.exit_mach,
            }
        save_design_json(state, output)
        console.print(f"\n[dim]Saved to {output}[/dim]")
