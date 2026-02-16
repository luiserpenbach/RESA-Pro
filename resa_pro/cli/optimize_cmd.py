"""CLI commands for design optimisation."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion
from resa_pro.optimization.optimizer import (
    Constraint,
    DesignOptimizer,
    DesignVariable,
    Objective,
)


def _default_engine_eval(params: dict[str, float]) -> dict[str, float]:
    """Default evaluation function for engine-level optimisation.

    Varies chamber pressure and expansion ratio, computes performance.
    """
    pc = params.get("chamber_pressure", 2e6)
    eps = params.get("expansion_ratio", 10.0)
    mr = params.get("mixture_ratio", 4.0)

    ox = params.get("_oxidizer", "n2o")
    fuel = params.get("_fuel", "ethanol")

    try:
        comb = lookup_combustion(str(ox), str(fuel), mixture_ratio=mr)
        perf = compute_nozzle_performance(
            gamma=comb.gamma,
            molar_mass=comb.molar_mass,
            Tc=comb.chamber_temperature,
            expansion_ratio=eps,
            pc=pc,
        )
        return {
            "Isp_vac": perf.Isp_vac,
            "Isp_sl": perf.Isp_sl,
            "CF_vac": perf.CF_vac,
            "c_star": perf.c_star,
            "exit_mach": perf.exit_mach,
            "pe_pc": perf.pe_pc,
        }
    except Exception:
        return {"Isp_vac": 0.0, "Isp_sl": 0.0, "CF_vac": 0.0, "c_star": 0.0}


@click.group("optimize")
@click.pass_context
def optimize(ctx: click.Context) -> None:
    """Design optimisation commands."""
    pass


@optimize.command("isp")
@click.option("--oxidizer", default="n2o", show_default=True, help="Oxidizer name.")
@click.option("--fuel", default="ethanol", show_default=True, help="Fuel name.")
@click.option("--pc-min", type=float, default=1e6, help="Min chamber pressure [Pa].")
@click.option("--pc-max", type=float, default=5e6, help="Max chamber pressure [Pa].")
@click.option("--eps-min", type=float, default=3.0, help="Min expansion ratio.")
@click.option("--eps-max", type=float, default=50.0, help="Max expansion ratio.")
@click.option(
    "--method",
    type=click.Choice(["nelder-mead", "differential_evolution", "l-bfgs-b"]),
    default="differential_evolution",
    show_default=True,
    help="Optimisation method.",
)
@click.option("--max-iter", type=int, default=100, show_default=True, help="Maximum iterations.")
@click.option("--seed", type=int, default=42, show_default=True, help="Random seed.")
@click.pass_context
def optimize_isp(
    ctx: click.Context,
    oxidizer: str,
    fuel: str,
    pc_min: float,
    pc_max: float,
    eps_min: float,
    eps_max: float,
    method: str,
    max_iter: int,
    seed: int,
) -> None:
    """Optimise expansion ratio and chamber pressure for maximum Isp."""
    console: Console = ctx.obj.get("console", Console())

    opt = DesignOptimizer()
    opt.add_variable(DesignVariable("chamber_pressure", pc_min, pc_max, unit="Pa"))
    opt.add_variable(DesignVariable("expansion_ratio", eps_min, eps_max))
    opt.add_objective(Objective("Isp_vac", "Isp_vac", direction="maximize"))

    def eval_func(params: dict[str, float]) -> dict[str, float]:
        params["_oxidizer"] = oxidizer
        params["_fuel"] = fuel
        return _default_engine_eval(params)

    result = opt.optimize(eval_func, method=method, max_iter=max_iter, seed=seed)

    console.print("\n[bold]RESA Pro — Isp Optimisation[/bold]\n")

    if result.best is not None:
        table = Table(title="Optimal Design Point")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green", justify="right")

        for name, val in result.best.variables.items():
            if name.startswith("_"):
                continue
            if "pressure" in name:
                table.add_row(name, f"{val / 1e5:.2f} bar")
            else:
                table.add_row(name, f"{val:.2f}")

        for name, val in result.best.objectives.items():
            table.add_row(f"[bold]{name}[/bold]", f"[bold]{val:.2f} s[/bold]")

        console.print(table)
        console.print(f"\n[dim]Evaluations: {result.n_evaluations} | Converged: {result.converged}[/dim]")
    else:
        console.print("[red]Optimisation failed — no feasible point found[/red]")


@optimize.command("sensitivity")
@click.option("--oxidizer", default="n2o", show_default=True, help="Oxidizer name.")
@click.option("--fuel", default="ethanol", show_default=True, help="Fuel name.")
@click.option("--pc", type=float, default=2e6, show_default=True, help="Base chamber pressure [Pa].")
@click.option("--eps", type=float, default=10.0, show_default=True, help="Base expansion ratio.")
@click.option("--perturbation", type=float, default=0.05, show_default=True, help="Perturbation fraction.")
@click.pass_context
def sensitivity_cmd(
    ctx: click.Context,
    oxidizer: str,
    fuel: str,
    pc: float,
    eps: float,
    perturbation: float,
) -> None:
    """Run one-at-a-time sensitivity analysis."""
    console: Console = ctx.obj.get("console", Console())

    opt = DesignOptimizer()
    opt.add_variable(DesignVariable("chamber_pressure", 1e6, 5e6, initial=pc, unit="Pa"))
    opt.add_variable(DesignVariable("expansion_ratio", 3.0, 50.0, initial=eps))
    opt.add_objective(Objective("Isp_vac", "Isp_vac"))
    opt.add_objective(Objective("CF_vac", "CF_vac"))

    def eval_func(params: dict[str, float]) -> dict[str, float]:
        params["_oxidizer"] = oxidizer
        params["_fuel"] = fuel
        return _default_engine_eval(params)

    sens = opt.sensitivity_analysis(eval_func, perturbation=perturbation)

    console.print("\n[bold]RESA Pro — Sensitivity Analysis[/bold]\n")

    table = Table(title="Normalised Sensitivities (Δf/f)/(Δx/x_range)")
    table.add_column("Variable", style="cyan")
    for obj in opt.objectives:
        table.add_column(obj.name, style="green", justify="right")

    for var_name, obj_sens in sens.items():
        row = [var_name]
        for obj in opt.objectives:
            val = obj_sens.get(obj.name, 0.0)
            row.append(f"{val:+.4f}")
        table.add_row(*row)

    console.print(table)


@optimize.command("doe")
@click.option("--oxidizer", default="n2o", show_default=True, help="Oxidizer name.")
@click.option("--fuel", default="ethanol", show_default=True, help="Fuel name.")
@click.option("--pc-min", type=float, default=1e6, help="Min chamber pressure [Pa].")
@click.option("--pc-max", type=float, default=5e6, help="Max chamber pressure [Pa].")
@click.option("--eps-min", type=float, default=3.0, help="Min expansion ratio.")
@click.option("--eps-max", type=float, default=50.0, help="Max expansion ratio.")
@click.option("--samples", "-n", type=int, default=20, show_default=True, help="Number of samples.")
@click.option("--seed", type=int, default=42, show_default=True, help="Random seed.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file (JSON).")
@click.pass_context
def doe_cmd(
    ctx: click.Context,
    oxidizer: str,
    fuel: str,
    pc_min: float,
    pc_max: float,
    eps_min: float,
    eps_max: float,
    samples: int,
    seed: int,
    output: str | None,
) -> None:
    """Run Latin Hypercube sampling of the design space."""
    console: Console = ctx.obj.get("console", Console())

    opt = DesignOptimizer()
    opt.add_variable(DesignVariable("chamber_pressure", pc_min, pc_max, unit="Pa"))
    opt.add_variable(DesignVariable("expansion_ratio", eps_min, eps_max))
    opt.add_objective(Objective("Isp_vac", "Isp_vac"))

    def eval_func(params: dict[str, float]) -> dict[str, float]:
        params["_oxidizer"] = oxidizer
        params["_fuel"] = fuel
        return _default_engine_eval(params)

    points = opt.doe_latin_hypercube(eval_func, n_samples=samples, seed=seed)

    console.print(f"\n[bold]RESA Pro — DOE ({samples} samples)[/bold]\n")

    # Show top 5 by Isp
    ranked = sorted(points, key=lambda p: p.objectives.get("Isp_vac", 0), reverse=True)

    table = Table(title=f"Top 5 of {len(ranked)} Samples")
    table.add_column("#", style="dim")
    table.add_column("Pc [bar]", style="cyan", justify="right")
    table.add_column("ε", style="cyan", justify="right")
    table.add_column("Isp_vac [s]", style="green", justify="right")

    for i, pt in enumerate(ranked[:5]):
        table.add_row(
            str(i + 1),
            f"{pt.variables.get('chamber_pressure', 0) / 1e5:.1f}",
            f"{pt.variables.get('expansion_ratio', 0):.1f}",
            f"{pt.objectives.get('Isp_vac', 0):.1f}",
        )

    console.print(table)

    if output:
        data = [
            {
                "variables": pt.variables,
                "objectives": pt.objectives,
                "feasible": pt.feasible,
            }
            for pt in ranked
        ]
        with open(output, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"\n[dim]Saved {len(data)} points to {output}[/dim]")
