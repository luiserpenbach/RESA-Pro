"""RESA Pro command-line interface.

Entry point for the ``resa`` CLI tool.
"""

from __future__ import annotations

import click
from rich.console import Console

from resa_pro import __app_name__, __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name=__app_name__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """RESA Pro — Rocket Engine Sizing and Analysis.

    A comprehensive tool for rocket engine design, analysis, and
    optimisation.
    """
    ctx.ensure_object(dict)
    ctx.obj["console"] = console


# Import and register sub-command groups
from resa_pro.cli.chamber_cmd import chamber  # noqa: E402
from resa_pro.cli.nozzle_cmd import nozzle  # noqa: E402
from resa_pro.cli.info_cmd import info  # noqa: E402
from resa_pro.cli.injector_cmd import injector  # noqa: E402
from resa_pro.cli.cooling_cmd import cooling  # noqa: E402
from resa_pro.cli.feed_cmd import feed  # noqa: E402
from resa_pro.cli.geometry_cmd import export_stl  # noqa: E402
from resa_pro.cli.report_cmd import report  # noqa: E402
from resa_pro.cli.cycle_cmd import cycle  # noqa: E402
from resa_pro.cli.optimize_cmd import optimize  # noqa: E402
from resa_pro.cli.uq_cmd import uq  # noqa: E402
from resa_pro.cli.gui_cmd import gui  # noqa: E402

cli.add_command(chamber)
cli.add_command(nozzle)
cli.add_command(info)
cli.add_command(injector)
cli.add_command(cooling)
cli.add_command(feed)
cli.add_command(export_stl)
cli.add_command(report)
cli.add_command(cycle)
cli.add_command(optimize)
cli.add_command(uq)
cli.add_command(gui)


def main() -> None:
    """Convenience wrapper for entry-point scripts."""
    cli()
