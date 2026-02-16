"""Performance & Thermal analysis tab for RESA Pro GUI."""

from __future__ import annotations

import traceback

import numpy as np
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from resa_pro.ui.widgets.param_input import ParamForm
from resa_pro.ui.widgets.plot_widget import PlotCanvas
from resa_pro.ui.widgets.result_display import LogPanel, ResultTable


class PerformanceTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        splitter = QSplitter()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(splitter)

        # --- Left: inputs ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self.form = ParamForm()
        self.form.add_header("Propellant Combination")
        self.form.add_combo("oxidizer", "Oxidizer", ["n2o", "lox", "h2o2"], default="n2o")
        self.form.add_combo("fuel", "Fuel", ["ethanol", "rp1", "methane", "hydrogen", "isopropanol"], default="ethanol")
        self.form.add_float("mixture_ratio", "Mixture Ratio (O/F)", 4.0, min_val=0.5, max_val=20, step=0.1)

        self.form.add_separator()
        self.form.add_header("Operating Conditions")
        self.form.add_float("chamber_pressure", "Chamber Pressure", 2e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.form.add_float("expansion_ratio", "Expansion Ratio", 10.0, min_val=1.1, max_val=300, step=0.5)
        self.form.add_float("ambient_pressure", "Ambient Pressure", 101325.0, unit="Pa", min_val=0, max_val=2e5, step=1000)

        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        left_layout.addWidget(scroll)

        btn = QPushButton("Compute Performance")
        btn.clicked.connect(self._compute)
        left_layout.addWidget(btn)

        btn_sweep = QPushButton("Sweep Expansion Ratio")
        btn_sweep.setProperty("secondary", True)
        btn_sweep.clicked.connect(self._sweep_eps)
        left_layout.addWidget(btn_sweep)

        # --- Right: results ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.results = ResultTable("Nozzle Performance")
        right_layout.addWidget(self.results)

        self.plot = PlotCanvas("Performance Sweep")
        right_layout.addWidget(self.plot)

        self.log = LogPanel("Log")
        self.log.setMaximumHeight(100)
        right_layout.addWidget(self.log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([350, 650])

    def _compute(self) -> None:
        self.log.clear()
        self.results.clear()
        try:
            v = self.form.get_values()
            from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion

            comb = lookup_combustion(v["oxidizer"], v["fuel"], mixture_ratio=v["mixture_ratio"])
            perf = compute_nozzle_performance(
                gamma=comb.gamma,
                molar_mass=comb.molar_mass,
                Tc=comb.chamber_temperature,
                expansion_ratio=v["expansion_ratio"],
                pc=v["chamber_pressure"],
                pa=v["ambient_pressure"],
            )

            rows = [
                ("Chamber Temperature", f"{comb.chamber_temperature:.0f}", "K"),
                ("Gamma", f"{comb.gamma:.3f}", ""),
                ("Molar Mass", f"{comb.molar_mass:.4f}", "kg/mol"),
                ("", "", ""),
                ("c* (characteristic velocity)", f"{perf.c_star:.1f}", "m/s"),
                ("CF (vacuum)", f"{perf.CF_vac:.4f}", ""),
                ("CF (sea level)", f"{perf.CF_sl:.4f}", ""),
                ("Isp (vacuum)", f"{perf.Isp_vac:.1f}", "s"),
                ("Isp (sea level)", f"{perf.Isp_sl:.1f}", "s"),
                ("Exhaust Velocity (vac)", f"{perf.ve_vac:.1f}", "m/s"),
                ("Exit Mach Number", f"{perf.exit_mach:.3f}", ""),
                ("Exit Pressure Ratio (Pe/Pc)", f"{perf.pe_pc:.6f}", ""),
            ]
            self.results.set_data(rows)
            self.log.log(f"Isp_vac = {perf.Isp_vac:.1f} s, c* = {perf.c_star:.1f} m/s")

        except Exception as e:
            self.log.log(f"ERROR: {e}")
            self.log.log(traceback.format_exc())

    def _sweep_eps(self) -> None:
        """Sweep expansion ratio and plot Isp vs epsilon."""
        self.log.clear()
        try:
            v = self.form.get_values()
            from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion

            comb = lookup_combustion(v["oxidizer"], v["fuel"], mixture_ratio=v["mixture_ratio"])

            eps_range = np.linspace(2, 80, 60)
            isp_vac = []
            isp_sl = []

            for eps in eps_range:
                perf = compute_nozzle_performance(
                    gamma=comb.gamma,
                    molar_mass=comb.molar_mass,
                    Tc=comb.chamber_temperature,
                    expansion_ratio=eps,
                    pc=v["chamber_pressure"],
                    pa=v["ambient_pressure"],
                )
                isp_vac.append(perf.Isp_vac)
                isp_sl.append(perf.Isp_sl)

            self.plot.plot_multi(
                [
                    (eps_range, isp_vac, "Isp vacuum"),
                    (eps_range, isp_sl, "Isp sea level"),
                ],
                xlabel="Expansion Ratio",
                ylabel="Isp [s]",
                title="Isp vs Expansion Ratio",
            )
            self.log.log(f"Sweep complete: eps = 2..80, max Isp_vac = {max(isp_vac):.1f} s")

        except Exception as e:
            self.log.log(f"ERROR: {e}")
            self.log.log(traceback.format_exc())
