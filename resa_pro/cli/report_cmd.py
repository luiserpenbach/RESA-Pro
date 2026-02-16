"""CLI commands for report generation."""

from __future__ import annotations

import click
from rich.console import Console

from resa_pro.core.config import load_design_json
from resa_pro.reports.summary import (
    generate_text_report,
    save_html_report,
    save_text_report,
)


@click.command("report")
@click.option(
    "--design",
    type=click.Path(exists=True),
    required=True,
    help="Input design JSON.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "html", "both"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Report format.",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Output file path (auto-generated if not specified).",
)
@click.pass_context
def report(
    ctx: click.Context,
    design: str,
    fmt: str,
    output: str | None,
) -> None:
    """Generate a design summary report."""
    console: Console = ctx.obj.get("console", Console())

    state = load_design_json(design)

    if fmt == "text" or fmt == "both":
        out_txt = output or "report.txt"
        if fmt == "both" and output:
            out_txt = output.rsplit(".", 1)[0] + ".txt"
        save_text_report(state, out_txt)
        console.print(f"[green]Text report saved:[/green] {out_txt}")

    if fmt == "html" or fmt == "both":
        out_html = output or "report.html"
        if fmt == "both" and output:
            out_html = output.rsplit(".", 1)[0] + ".html"
        save_html_report(state, out_html)
        console.print(f"[green]HTML report saved:[/green] {out_html}")

    if fmt == "text" and not output:
        # Print to console as well
        text = generate_text_report(state)
        console.print(f"\n{text}")
