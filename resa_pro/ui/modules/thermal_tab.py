"""Thermal analysis tab for RESA Pro GUI."""

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


class ThermalTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        splitter = QSplitter()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(splitter)

        # --- Left ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self.form = ParamForm()
        self.form.add_header("Operating Conditions")
        self.form.add_float("pc", "Chamber Pressure", 2e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.form.add_float("Tc", "Chamber Temperature", 3100.0, unit="K", min_val=500, max_val=5000, step=50)
        self.form.add_float("gamma", "Gamma", 1.21, min_val=1.05, max_val=1.67, step=0.01)
        self.form.add_float("molar_mass", "Molar Mass", 0.026, unit="kg/mol", min_val=0.001, max_val=0.1, step=0.001)
        self.form.add_float("c_star", "c*", 1550.0, unit="m/s", min_val=500, max_val=3000, step=10)

        self.form.add_separator()
        self.form.add_header("Geometry")
        self.form.add_float("throat_radius", "Throat Radius", 15.0, unit="mm", min_val=1, max_val=500, step=0.5)
        self.form.add_float("expansion_ratio", "Expansion Ratio", 10.0, min_val=1.5, max_val=100, step=0.5)

        self.form.add_separator()
        self.form.add_header("Wall")
        self.form.add_float("T_wall", "Wall Temperature", 600.0, unit="K", min_val=200, max_val=3000, step=10)

        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        left_layout.addWidget(scroll)

        btn = QPushButton("Compute Heat Flux")
        btn.clicked.connect(self._compute)
        left_layout.addWidget(btn)

        # --- Right ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.results = ResultTable("Thermal Results")
        right_layout.addWidget(self.results)

        self.plot = PlotCanvas("Heat Flux Distribution")
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
            from resa_pro.core.chamber import size_chamber_from_dimensions, generate_chamber_contour
            from resa_pro.core.nozzle import parabolic_nozzle
            from resa_pro.core.thermal import compute_heat_flux_distribution

            throat_r = v["throat_radius"] / 1e3
            # Create a simple chamber+nozzle contour
            geom = size_chamber_from_dimensions(
                throat_diameter=throat_r * 2,
                contraction_ratio=3.0,
                l_star=1.2,
            )
            cx, cy = generate_chamber_contour(geom)

            noz = parabolic_nozzle(throat_r, v["expansion_ratio"])
            # Combine contours
            full_x = list(cx) + [x + cx[-1] for x in noz.x[1:]]
            full_y = list(cy) + list(noz.y[1:])

            hf_results = compute_heat_flux_distribution(
                contour_x=full_x,
                contour_y=full_y,
                throat_radius=throat_r,
                pc=v["pc"],
                c_star=v["c_star"],
                Tc=v["Tc"],
                gamma=v["gamma"],
                molar_mass=v["molar_mass"],
                T_wall=v["T_wall"],
            )

            # Extract data for plotting and display
            x_arr = [r.x * 1e3 for r in hf_results]
            q_arr = [r.q_dot / 1e6 for r in hf_results]
            hg_arr = [r.h_g for r in hf_results]

            peak_q = max(r.q_dot for r in hf_results)
            peak_hg = max(r.h_g for r in hf_results)
            peak_taw = max(r.T_aw for r in hf_results)

            rows = [
                ("Peak Heat Flux", f"{peak_q / 1e6:.2f}", "MW/m^2"),
                ("Peak h_g", f"{peak_hg:.0f}", "W/(m^2.K)"),
                ("Peak Adiabatic Wall Temp", f"{peak_taw:.0f}", "K"),
                ("Wall Temperature", f"{v['T_wall']:.0f}", "K"),
                ("Stations Computed", f"{len(hf_results)}", ""),
            ]
            self.results.set_data(rows)

            self.plot.plot(
                x_arr, q_arr,
                xlabel="x [mm]", ylabel="q [MW/m^2]",
                title="Heat Flux Distribution Along Wall",
                color="coral",
            )

            self.log.log(f"Peak heat flux: {peak_q/1e6:.2f} MW/m^2 at throat region")

        except Exception as e:
            self.log.log(f"ERROR: {e}")
            self.log.log(traceback.format_exc())
