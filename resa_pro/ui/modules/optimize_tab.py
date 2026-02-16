"""Optimization & UQ tab for RESA Pro GUI."""

from __future__ import annotations

import traceback

import numpy as np
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from resa_pro.ui.widgets.param_input import ParamForm
from resa_pro.ui.widgets.plot_widget import PlotCanvas
from resa_pro.ui.widgets.result_display import LogPanel, ResultTable


class OptimizeUQTab(QWidget):
    """Combined optimization and uncertainty quantification tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        tabs = QTabWidget()
        tabs.addTab(self._build_optimize_panel(), "Optimization")
        tabs.addTab(self._build_doe_panel(), "DOE")
        tabs.addTab(self._build_uq_panel(), "Uncertainty (MC)")
        layout.addWidget(tabs)

    # ---------- Optimization ----------

    def _build_optimize_panel(self) -> QWidget:
        w = QWidget()
        splitter = QSplitter()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        self.opt_form = ParamForm()
        self.opt_form.add_header("Design Space")
        self.opt_form.add_combo("oxidizer", "Oxidizer", ["n2o", "lox"], default="n2o")
        self.opt_form.add_combo("fuel", "Fuel", ["ethanol", "rp1", "methane", "hydrogen"], default="ethanol")
        self.opt_form.add_float("pc_min", "Pc min", 1e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.opt_form.add_float("pc_max", "Pc max", 5e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.opt_form.add_float("eps_min", "Epsilon min", 3.0, min_val=1.5, max_val=50, step=0.5)
        self.opt_form.add_float("eps_max", "Epsilon max", 50.0, min_val=2, max_val=300, step=1)

        self.opt_form.add_separator()
        self.opt_form.add_header("Optimizer Settings")
        self.opt_form.add_combo("method", "Method", ["differential_evolution", "nelder-mead", "l-bfgs-b"])
        self.opt_form.add_int("max_iter", "Max Iterations", 100, min_val=10, max_val=5000)
        self.opt_form.add_int("seed", "Random Seed", 42, min_val=0, max_val=99999)

        scroll = QScrollArea()
        scroll.setWidget(self.opt_form)
        scroll.setWidgetResizable(True)
        ll.addWidget(scroll)

        btn = QPushButton("Optimize Isp")
        btn.clicked.connect(self._run_optimize)
        ll.addWidget(btn)

        btn_sens = QPushButton("Sensitivity Analysis")
        btn_sens.setProperty("secondary", True)
        btn_sens.clicked.connect(self._run_sensitivity)
        ll.addWidget(btn_sens)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.opt_results = ResultTable("Optimization Result")
        rl.addWidget(self.opt_results)
        self.opt_plot = PlotCanvas("Design Space")
        rl.addWidget(self.opt_plot)
        self.opt_log = LogPanel("Log")
        self.opt_log.setMaximumHeight(80)
        rl.addWidget(self.opt_log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 620])
        return w

    # ---------- DOE ----------

    def _build_doe_panel(self) -> QWidget:
        w = QWidget()
        splitter = QSplitter()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        self.doe_form = ParamForm()
        self.doe_form.add_header("DOE Settings")
        self.doe_form.add_combo("oxidizer", "Oxidizer", ["n2o", "lox"], default="n2o")
        self.doe_form.add_combo("fuel", "Fuel", ["ethanol", "rp1", "methane", "hydrogen"], default="ethanol")
        self.doe_form.add_float("pc_min", "Pc min", 1e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.doe_form.add_float("pc_max", "Pc max", 5e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.doe_form.add_float("eps_min", "Eps min", 3.0, min_val=1.5, max_val=50, step=0.5)
        self.doe_form.add_float("eps_max", "Eps max", 50.0, min_val=2, max_val=300, step=1)
        self.doe_form.add_int("n_samples", "Samples", 50, min_val=5, max_val=5000)
        self.doe_form.add_int("seed", "Seed", 42, min_val=0, max_val=99999)

        scroll = QScrollArea()
        scroll.setWidget(self.doe_form)
        scroll.setWidgetResizable(True)
        ll.addWidget(scroll)

        btn = QPushButton("Run DOE")
        btn.clicked.connect(self._run_doe)
        ll.addWidget(btn)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.doe_results = ResultTable("Top 5 Points")
        rl.addWidget(self.doe_results)
        self.doe_plot = PlotCanvas("DOE Scatter")
        rl.addWidget(self.doe_plot)
        self.doe_log = LogPanel("Log")
        self.doe_log.setMaximumHeight(80)
        rl.addWidget(self.doe_log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 620])
        return w

    # ---------- UQ ----------

    def _build_uq_panel(self) -> QWidget:
        w = QWidget()
        splitter = QSplitter()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        self.uq_form = ParamForm()
        self.uq_form.add_header("Nominal + Uncertainty")
        self.uq_form.add_float("pc", "Pc (nominal)", 2e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.uq_form.add_float("pc_std", "Pc std dev", 0.1e6, unit="Pa", min_val=0, max_val=5e6, step=1e4)
        self.uq_form.add_float("mr", "MR (nominal)", 4.0, min_val=0.5, max_val=20, step=0.1)
        self.uq_form.add_float("mr_std", "MR std dev", 0.2, min_val=0, max_val=5, step=0.01)
        self.uq_form.add_float("eps", "Eps (nominal)", 10.0, min_val=1.5, max_val=300, step=0.5)
        self.uq_form.add_float("eps_std", "Eps std dev", 0.5, min_val=0, max_val=30, step=0.1)

        self.uq_form.add_separator()
        self.uq_form.add_header("Monte Carlo Settings")
        self.uq_form.add_int("n_samples", "Samples", 1000, min_val=50, max_val=50000)
        self.uq_form.add_int("seed", "Seed", 42, min_val=0, max_val=99999)

        scroll = QScrollArea()
        scroll.setWidget(self.uq_form)
        scroll.setWidgetResizable(True)
        ll.addWidget(scroll)

        btn = QPushButton("Run Monte Carlo")
        btn.clicked.connect(self._run_uq)
        ll.addWidget(btn)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.uq_results = ResultTable("Output Statistics")
        rl.addWidget(self.uq_results)
        self.uq_plot = PlotCanvas("Isp Distribution")
        rl.addWidget(self.uq_plot)
        self.uq_log = LogPanel("Log")
        self.uq_log.setMaximumHeight(80)
        rl.addWidget(self.uq_log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 620])
        return w

    # ---------- Callbacks ----------

    def _eval_engine(self, params: dict) -> dict:
        from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion

        pc = params.get("chamber_pressure", 2e6)
        eps = params.get("expansion_ratio", 10.0)
        mr = params.get("mixture_ratio", 4.0)
        ox = params.get("_oxidizer", "n2o")
        fuel = params.get("_fuel", "ethanol")

        comb = lookup_combustion(str(ox), str(fuel), mixture_ratio=mr)
        perf = compute_nozzle_performance(
            gamma=comb.gamma, molar_mass=comb.molar_mass,
            Tc=comb.chamber_temperature, expansion_ratio=max(eps, 1.1), pc=max(pc, 1e5),
        )
        return {"Isp_vac": perf.Isp_vac, "CF_vac": perf.CF_vac, "c_star": perf.c_star}

    def _run_optimize(self) -> None:
        self.opt_log.clear()
        self.opt_results.clear()
        try:
            v = self.opt_form.get_values()
            from resa_pro.optimization.optimizer import DesignOptimizer, DesignVariable, Objective

            opt = DesignOptimizer()
            opt.add_variable(DesignVariable("chamber_pressure", v["pc_min"], v["pc_max"], unit="Pa"))
            opt.add_variable(DesignVariable("expansion_ratio", v["eps_min"], v["eps_max"]))
            opt.add_objective(Objective("Isp_vac", "Isp_vac", direction="maximize"))

            ox, fuel = v["oxidizer"], v["fuel"]

            def eval_fn(p):
                p["_oxidizer"] = ox
                p["_fuel"] = fuel
                return self._eval_engine(p)

            result = opt.optimize(eval_fn, method=v["method"], max_iter=v["max_iter"], seed=v["seed"])

            if result.best:
                rows = [
                    ("Pc optimal", f"{result.best.variables.get('chamber_pressure', 0)/1e5:.2f}", "bar"),
                    ("Eps optimal", f"{result.best.variables.get('expansion_ratio', 0):.2f}", ""),
                    ("Isp_vac (best)", f"{result.best.objectives.get('Isp_vac', 0):.2f}", "s"),
                    ("", "", ""),
                    ("Evaluations", f"{result.n_evaluations}", ""),
                    ("Converged", f"{result.converged}", ""),
                ]
                self.opt_results.set_data(rows)

                # Plot convergence (Isp history)
                isp_hist = [p.objectives.get("Isp_vac", 0) for p in result.all_points if p.feasible]
                if isp_hist:
                    best_so_far = []
                    mx = 0
                    for val in isp_hist:
                        mx = max(mx, val)
                        best_so_far.append(mx)
                    self.opt_plot.plot(
                        list(range(len(best_so_far))), best_so_far,
                        xlabel="Evaluation", ylabel="Best Isp [s]",
                        title="Optimization Convergence", color="seagreen",
                    )

            self.opt_log.log(f"Optimization complete: {result.n_evaluations} evaluations")

        except Exception as e:
            self.opt_log.log(f"ERROR: {e}")
            self.opt_log.log(traceback.format_exc())

    def _run_sensitivity(self) -> None:
        self.opt_log.clear()
        try:
            v = self.opt_form.get_values()
            from resa_pro.optimization.optimizer import DesignOptimizer, DesignVariable, Objective

            opt = DesignOptimizer()
            pc_mid = (v["pc_min"] + v["pc_max"]) / 2
            eps_mid = (v["eps_min"] + v["eps_max"]) / 2
            opt.add_variable(DesignVariable("chamber_pressure", v["pc_min"], v["pc_max"], initial=pc_mid))
            opt.add_variable(DesignVariable("expansion_ratio", v["eps_min"], v["eps_max"], initial=eps_mid))
            opt.add_objective(Objective("Isp_vac", "Isp_vac"))

            ox, fuel = v["oxidizer"], v["fuel"]

            def eval_fn(p):
                p["_oxidizer"] = ox
                p["_fuel"] = fuel
                return self._eval_engine(p)

            sens = opt.sensitivity_analysis(eval_fn)

            rows = []
            labels = []
            values = []
            for var_name, obj_sens in sens.items():
                for obj_name, val in obj_sens.items():
                    rows.append((f"d({obj_name})/d({var_name})", f"{val:+.4f}", "normalised"))
                    labels.append(var_name)
                    values.append(abs(val))

            self.opt_results.set_data(rows)
            self.opt_plot.bar(labels, values, ylabel="|Sensitivity|", title="Sensitivity (normalised)")
            self.opt_log.log("Sensitivity analysis complete")

        except Exception as e:
            self.opt_log.log(f"ERROR: {e}")
            self.opt_log.log(traceback.format_exc())

    def _run_doe(self) -> None:
        self.doe_log.clear()
        self.doe_results.clear()
        try:
            v = self.doe_form.get_values()
            from resa_pro.optimization.optimizer import DesignOptimizer, DesignVariable, Objective

            opt = DesignOptimizer()
            opt.add_variable(DesignVariable("chamber_pressure", v["pc_min"], v["pc_max"]))
            opt.add_variable(DesignVariable("expansion_ratio", v["eps_min"], v["eps_max"]))
            opt.add_objective(Objective("Isp_vac", "Isp_vac"))

            ox, fuel = v["oxidizer"], v["fuel"]

            def eval_fn(p):
                p["_oxidizer"] = ox
                p["_fuel"] = fuel
                return self._eval_engine(p)

            points = opt.doe_latin_hypercube(eval_fn, n_samples=v["n_samples"], seed=v["seed"])
            ranked = sorted(points, key=lambda p: p.objectives.get("Isp_vac", 0), reverse=True)

            rows = []
            for i, pt in enumerate(ranked[:5]):
                rows.append((
                    f"#{i+1}",
                    f"Pc={pt.variables.get('chamber_pressure', 0)/1e5:.1f} bar, "
                    f"eps={pt.variables.get('expansion_ratio', 0):.1f}",
                    f"Isp={pt.objectives.get('Isp_vac', 0):.1f} s",
                ))
            self.doe_results.set_data(rows)

            # Scatter plot
            pc_vals = [p.variables.get("chamber_pressure", 0) / 1e5 for p in points]
            isp_vals = [p.objectives.get("Isp_vac", 0) for p in points]
            self.doe_plot.scatter(pc_vals, isp_vals, xlabel="Pc [bar]", ylabel="Isp_vac [s]", title="DOE Results")

            self.doe_log.log(f"DOE complete: {len(points)} samples, best Isp = {ranked[0].objectives.get('Isp_vac', 0):.1f} s")

        except Exception as e:
            self.doe_log.log(f"ERROR: {e}")
            self.doe_log.log(traceback.format_exc())

    def _run_uq(self) -> None:
        self.uq_log.clear()
        self.uq_results.clear()
        try:
            v = self.uq_form.get_values()
            from resa_pro.optimization.uq import Distribution, UncertainParameter, UncertaintyAnalysis

            uq = UncertaintyAnalysis()
            uq.add_parameter(UncertainParameter("chamber_pressure", v["pc"], Distribution.NORMAL, std=v["pc_std"], unit="Pa"))
            uq.add_parameter(UncertainParameter("mixture_ratio", v["mr"], Distribution.NORMAL, std=v["mr_std"]))
            uq.add_parameter(UncertainParameter("expansion_ratio", v["eps"], Distribution.NORMAL, std=v["eps_std"]))
            uq.add_output("Isp_vac")
            uq.add_output("c_star")
            uq.add_output("CF_vac")

            def eval_fn(p):
                p["_oxidizer"] = "n2o"
                p["_fuel"] = "ethanol"
                return self._eval_engine(p)

            result = uq.run(eval_fn, n_samples=v["n_samples"], seed=v["seed"])

            rows = []
            for key, stats in result.output_statistics.items():
                rows.append((key, f"{stats.mean:.2f} +/- {stats.std:.2f}", f"95% CI: [{stats.ci_95_lower:.2f}, {stats.ci_95_upper:.2f}]"))
            if result.n_failed > 0:
                rows.append(("Failed samples", f"{result.n_failed}", ""))
            self.uq_results.set_data(rows)

            # Histogram of Isp
            if "Isp_vac" in result.output_statistics:
                samples = result.output_statistics["Isp_vac"].samples
                self.uq_plot.ax.clear()
                self.uq_plot.ax.hist(samples, bins=40, color="steelblue", alpha=0.7, edgecolor="none")
                self.uq_plot.ax.set_xlabel("Isp_vac [s]", fontsize=9)
                self.uq_plot.ax.set_ylabel("Count", fontsize=9)
                self.uq_plot.ax.set_title("Isp Distribution (Monte Carlo)", fontsize=10)
                self.uq_plot.ax.grid(True, alpha=0.3, axis="y")
                mean = result.output_statistics["Isp_vac"].mean
                self.uq_plot.ax.axvline(mean, color="coral", linestyle="--", linewidth=1.5, label=f"Mean={mean:.1f}")
                self.uq_plot.ax.legend(fontsize=8)
                self.uq_plot.figure.tight_layout()
                self.uq_plot._canvas.draw()

            self.uq_log.log(f"MC complete: {v['n_samples']} samples, {result.n_failed} failed")

        except Exception as e:
            self.uq_log.log(f"ERROR: {e}")
            self.uq_log.log(traceback.format_exc())
