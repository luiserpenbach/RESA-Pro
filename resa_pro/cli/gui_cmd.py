"""CLI command to launch the RESA Pro desktop GUI."""

from __future__ import annotations

import click


@click.command("gui")
def gui() -> None:
    """Launch the RESA Pro desktop application."""
    try:
        from resa_pro.ui.app import run

        run()
    except ImportError as e:
        click.echo(
            f"GUI dependencies not installed: {e}\n"
            f"Install with: pip install -e '.[ui]'"
        )
        raise SystemExit(1)
