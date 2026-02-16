"""CLI commands for uncertainty quantification."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion
from resa_pro.optimization.uq import (
    Distribution,
    UncertainParameter,
    UncertaintyAnalysis,
)


def _engine_uq_eval(params: dict[str, float]) -> dict[str, float]:
    """Evaluation function for engine UQ with uncertain Pc, MR, gamma."""
    pc = params.get("chamber_pressure", 2e6)
    mr = params.get("mixture_ratio", 4.0)
    eps = params.get("expansion_ratio", 10.0)

    comb = lookup_combustion("n2o", "ethanol", mixture_ratio=mr)
    perf = compute_nozzle_performance(
        gamma=comb.gamma,
        molar_mass=comb.molar_mass,
        Tc=comb.chamber_temperature,
        expansion_ratio=max(eps, 1.1),
        pc=max(pc, 1e5),
    )
    return {
        "Isp_vac": perf.Isp_vac,
        "Isp_sl": perf.Isp_sl,
        "c_star": perf.c_star,
        "CF_vac": perf.CF_vac,
    }


@click.group("uq")
@click.pass_context
def uq(ctx: click.Context) -> None:
    """Uncertainty quantification commands."""
    pass


@uq.command("monte-carlo")
@click.option("--pc", type=float, default=2e6, show_default=True, help="Nominal chamber pressure [Pa].")
@click.option("--pc-std", type=float, default=0.1e6, show_default=True, help="Chamber pressure std dev [Pa].")
@click.option("--mr", type=float, default=4.0, show_default=True, help="Nominal mixture ratio.")
@click.option("--mr-std", type=float, default=0.2, show_default=True, help="Mixture ratio std dev.")
@click.option("--eps", type=float, default=10.0, show_default=True, help="Nominal expansion ratio.")
@click.option("--eps-std", type=float, default=0.5, show_default=True, help="Expansion ratio std dev.")
@click.option("--samples", "-n", type=int, default=1000, show_default=True, help="Number of MC samples.")
@click.option("--seed", type=int, default=42, show_default=True, help="Random seed.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def monte_carlo_cmd(
    ctx: click.Context,
    pc: float,
    pc_std: float,
    mr: float,
    mr_std: float,
    eps: float,
    eps_std: float,
    samples: int,
    seed: int,
    output: str | None,
) -> None:
    """Run Monte Carlo uncertainty propagation on engine performance."""
    console: Console = ctx.obj.get("console", Console())

    uq_engine = UncertaintyAnalysis()
    uq_engine.add_parameter(UncertainParameter(
        "chamber_pressure", pc, Distribution.NORMAL, std=pc_std, unit="Pa",
    ))
    uq_engine.add_parameter(UncertainParameter(
        "mixture_ratio", mr, Distribution.NORMAL, std=mr_std,
    ))
    uq_engine.add_parameter(UncertainParameter(
        "expansion_ratio", eps, Distribution.NORMAL, std=eps_std,
    ))
    uq_engine.add_output("Isp_vac")
    uq_engine.add_output("c_star")
    uq_engine.add_output("CF_vac")

    result = uq_engine.run(_engine_uq_eval, n_samples=samples, seed=seed)

    console.print(f"\n[bold]RESA Pro — Monte Carlo UQ ({samples} samples)[/bold]\n")

    # Output statistics
    stat_table = Table(title="Output Statistics")
    stat_table.add_column("Output", style="cyan")
    stat_table.add_column("Mean", style="green", justify="right")
    stat_table.add_column("Std", style="yellow", justify="right")
    stat_table.add_column("95% CI", style="dim", justify="right")

    for key, stats in result.output_statistics.items():
        stat_table.add_row(
            key,
            f"{stats.mean:.2f}",
            f"{stats.std:.2f}",
            f"[{stats.ci_95_lower:.2f}, {stats.ci_95_upper:.2f}]",
        )

    console.print(stat_table)

    # Sensitivity indices
    if result.sensitivity_indices:
        sens_table = Table(title="First-Order Sensitivity Indices")
        sens_table.add_column("Parameter", style="cyan")
        for key in uq_engine.output_keys:
            sens_table.add_column(key, style="green", justify="right")

        for param_name, indices in result.sensitivity_indices.items():
            row = [param_name]
            for key in uq_engine.output_keys:
                row.append(f"{indices.get(key, 0.0):.4f}")
            sens_table.add_row(*row)

        console.print(sens_table)

    # Correlations
    if result.correlation_matrix:
        corr_table = Table(title="Input-Output Correlations")
        corr_table.add_column("Parameter", style="cyan")
        for key in uq_engine.output_keys:
            corr_table.add_column(key, style="green", justify="right")

        for param_name, corrs in result.correlation_matrix.items():
            row = [param_name]
            for key in uq_engine.output_keys:
                val = corrs.get(key, 0.0)
                row.append(f"{val:+.4f}")
            corr_table.add_row(*row)

        console.print(corr_table)

    if result.n_failed > 0:
        console.print(f"\n[yellow]Warning: {result.n_failed} samples failed[/yellow]")

    if output:
        data = {
            "n_samples": result.n_samples,
            "n_failed": result.n_failed,
            "statistics": {
                key: {
                    "mean": s.mean,
                    "std": s.std,
                    "median": s.median,
                    "p05": s.p05,
                    "p95": s.p95,
                    "ci_95": [s.ci_95_lower, s.ci_95_upper],
                }
                for key, s in result.output_statistics.items()
            },
            "sensitivity_indices": result.sensitivity_indices,
            "correlations": result.correlation_matrix,
        }
        with open(output, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"\n[dim]Saved to {output}[/dim]")
