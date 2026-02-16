"""CLI commands for chamber sizing."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from resa_pro.core.chamber import size_chamber_from_thrust, size_chamber_from_dimensions
from resa_pro.core.config import DesignState, ProjectMeta, save_design_json


@click.command("chamber")
@click.option("--thrust", type=float, help="Design thrust [N].")
@click.option("--pc", type=float, help="Chamber pressure [Pa].")
@click.option(
    "--oxidizer", type=str, default="n2o", show_default=True, help="Oxidizer name."
)
@click.option(
    "--fuel", type=str, default="ethanol", show_default=True, help="Fuel name."
)
@click.option("--mr", type=float, default=None, help="Mixture ratio O/F (optional).")
@click.option(
    "--l-star", type=float, default=1.2, show_default=True, help="Characteristic length L* [m]."
)
@click.option(
    "--cr",
    type=float,
    default=3.0,
    show_default=True,
    help="Contraction ratio Ac/At.",
)
@click.option(
    "--throat-diameter",
    type=float,
    default=None,
    help="Throat diameter [m] (direct sizing mode).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path (JSON).",
)
@click.pass_context
def chamber(
    ctx: click.Context,
    thrust: float | None,
    pc: float | None,
    oxidizer: str,
    fuel: str,
    mr: float | None,
    l_star: float,
    cr: float,
    throat_diameter: float | None,
    output: str | None,
) -> None:
    """Size a combustion chamber from thrust/Pc or direct dimensions."""
    console: Console = ctx.obj.get("console", Console())

    if throat_diameter is not None:
        # Direct sizing mode
        geom = size_chamber_from_dimensions(
            throat_diameter=throat_diameter,
            contraction_ratio=cr,
            l_star=l_star,
        )
        console.print(f"\n[bold]RESA Pro — Chamber Sizing (direct)[/bold]\n")
    elif thrust is not None and pc is not None:
        geom = size_chamber_from_thrust(
            thrust=thrust,
            chamber_pressure=pc,
            oxidizer=oxidizer,
            fuel=fuel,
            mixture_ratio=mr,
            l_star=l_star,
            contraction_ratio=cr,
        )
        console.print(f"\n[bold]RESA Pro — Chamber Sizing[/bold]\n")
    else:
        console.print(
            "[red]Error:[/red] Provide either --thrust and --pc, or --throat-diameter."
        )
        raise SystemExit(1)

    # Display results
    table = Table(title="Chamber Design Results")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_column("Unit", style="dim")

    table.add_row("Throat Diameter", f"{geom.throat_diameter * 1e3:.2f}", "mm")
    table.add_row("Throat Area", f"{geom.throat_area * 1e4:.4f}", "cm²")
    table.add_row("Chamber Diameter", f"{geom.chamber_diameter * 1e3:.2f}", "mm")
    table.add_row("Chamber Length", f"{geom.chamber_length * 1e3:.2f}", "mm")
    table.add_row("Contraction Ratio", f"{geom.contraction_ratio:.2f}", "—")
    table.add_row("L*", f"{geom.l_star:.3f}", "m")
    table.add_row("Chamber Volume", f"{geom.chamber_volume * 1e6:.2f}", "cm³")
    table.add_row("Convergent Length", f"{geom.convergent_length * 1e3:.2f}", "mm")
    if geom.mass_flow > 0:
        table.add_row("Mass Flow Rate", f"{geom.mass_flow:.4f}", "kg/s")
    if geom.mixture_ratio > 0:
        table.add_row("Mixture Ratio (O/F)", f"{geom.mixture_ratio:.2f}", "—")

    console.print(table)

    # Save to file
    if output:
        state = DesignState(
            meta=ProjectMeta(name="Chamber Design"),
            oxidizer=oxidizer,
            fuel=fuel,
            mixture_ratio=mr or geom.mixture_ratio,
            chamber_pressure=pc or 0.0,
            thrust=thrust or 0.0,
            chamber={
                "throat_diameter": geom.throat_diameter,
                "throat_area": geom.throat_area,
                "chamber_diameter": geom.chamber_diameter,
                "chamber_length": geom.chamber_length,
                "contraction_ratio": geom.contraction_ratio,
                "l_star": geom.l_star,
                "chamber_volume": geom.chamber_volume,
                "convergent_length": geom.convergent_length,
                "convergent_half_angle_deg": geom.convergent_half_angle * 180 / 3.14159,
                "throat_upstream_radius": geom.throat_upstream_radius,
                "throat_downstream_radius": geom.throat_downstream_radius,
                "mass_flow": geom.mass_flow,
                "contour_x": geom.contour_x.tolist(),
                "contour_y": geom.contour_y.tolist(),
            },
        )
        save_design_json(state, output)
        console.print(f"\n[dim]Saved to {output}[/dim]")
