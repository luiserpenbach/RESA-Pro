"""CLI commands for 3D geometry generation."""

from __future__ import annotations

import click
from rich.console import Console

from resa_pro.core.config import load_design_json


@click.command("export-stl")
@click.option(
    "--design",
    type=click.Path(exists=True),
    required=True,
    help="Input design JSON (must have contour data).",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="engine.stl",
    show_default=True,
    help="Output STL file path.",
)
@click.option(
    "--segments",
    type=int,
    default=64,
    show_default=True,
    help="Circumferential mesh divisions.",
)
@click.option(
    "--format",
    "stl_format",
    type=click.Choice(["binary", "ascii"], case_sensitive=False),
    default="binary",
    show_default=True,
    help="STL format.",
)
@click.pass_context
def export_stl(
    ctx: click.Context,
    design: str,
    output: str,
    segments: int,
    stl_format: str,
) -> None:
    """Export a 3D STL model from chamber + nozzle contours."""
    import numpy as np

    from resa_pro.geometry3d.engine import (
        combine_contours,
        export_stl_ascii,
        export_stl_binary,
        revolve_contour,
    )

    console: Console = ctx.obj.get("console", Console())

    state = load_design_json(design)

    # Get contours
    ch_x = state.chamber.get("contour_x")
    ch_y = state.chamber.get("contour_y")
    nz_x = state.nozzle.get("contour_x")
    nz_y = state.nozzle.get("contour_y")

    if ch_x is None or ch_y is None:
        console.print("[red]Error:[/red] Design file missing chamber contour data.")
        raise SystemExit(1)

    ch_x = np.asarray(ch_x)
    ch_y = np.asarray(ch_y)

    if nz_x is not None and nz_y is not None:
        nz_x = np.asarray(nz_x)
        nz_y = np.asarray(nz_y)
        x, y = combine_contours(ch_x, ch_y, nz_x, nz_y)
        console.print("[dim]Combined chamber + nozzle contour[/dim]")
    else:
        x, y = ch_x, ch_y
        console.print("[dim]Chamber contour only (no nozzle data)[/dim]")

    mesh = revolve_contour(x, y, n_circumferential=segments)

    if stl_format.lower() == "ascii":
        export_stl_ascii(mesh, output)
    else:
        export_stl_binary(mesh, output)

    console.print(
        f"\n[bold]RESA Pro — STL Export[/bold]\n\n"
        f"  Vertices:  {mesh.n_vertices}\n"
        f"  Faces:     {mesh.n_faces}\n"
        f"  Saved to:  {output}\n"
    )
