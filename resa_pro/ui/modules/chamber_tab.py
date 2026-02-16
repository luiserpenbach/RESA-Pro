"""Chamber design tab for RESA Pro GUI."""

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


class ChamberTab(QWidget):
    def __init__(self, parent: QWidget | None = None, shared: object | None = None) -> None:
        super().__init__(parent)
        self._shared = shared
        splitter = QSplitter()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(splitter)

        # --- Left: inputs ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self.form = ParamForm()
        self.form.add_header("Operating Point")
        self.form.add_float("thrust", "Thrust", 2000.0, unit="N", min_val=1, max_val=1e8, step=100)
        self.form.add_float("chamber_pressure", "Chamber Pressure", 2e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.form.add_combo("oxidizer", "Oxidizer", ["n2o", "lox", "h2o2"], default="n2o")
        self.form.add_combo("fuel", "Fuel", ["ethanol", "rp1", "methane", "hydrogen", "isopropanol"], default="ethanol")
        self.form.add_float("mixture_ratio", "Mixture Ratio (O/F)", 4.0, min_val=0.5, max_val=20, step=0.1)

        self.form.add_separator()
        self.form.add_header("Geometry Parameters")
        self.form.add_float("l_star", "L*", 1.2, unit="m", min_val=0.1, max_val=5.0, step=0.05)
        self.form.add_float("contraction_ratio", "Contraction Ratio", 3.5, min_val=1.2, max_val=10, step=0.1)
        self.form.add_float("conv_half_angle", "Convergent Half Angle", 30.0, unit="deg", min_val=10, max_val=60, step=1)

        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        left_layout.addWidget(scroll)

        btn = QPushButton("Compute Chamber")
        btn.clicked.connect(self._compute)
        left_layout.addWidget(btn)

        # --- Right: results ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.results = ResultTable("Chamber Geometry")
        right_layout.addWidget(self.results)

        self.plot = PlotCanvas("Chamber Contour")
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
            from resa_pro.core.chamber import size_chamber_from_thrust, generate_chamber_contour

            geom = size_chamber_from_thrust(
                thrust=v["thrust"],
                chamber_pressure=v["chamber_pressure"],
                oxidizer=v["oxidizer"],
                fuel=v["fuel"],
                mixture_ratio=v["mixture_ratio"],
                l_star=v["l_star"],
                contraction_ratio=v["contraction_ratio"],
                convergent_half_angle=v["conv_half_angle"],
            )

            rows = [
                ("Throat Diameter", f"{geom.throat_diameter * 1e3:.2f}", "mm"),
                ("Throat Radius", f"{geom.throat_radius * 1e3:.2f}", "mm"),
                ("Chamber Diameter", f"{geom.chamber_diameter * 1e3:.2f}", "mm"),
                ("Chamber Length", f"{geom.chamber_length * 1e3:.2f}", "mm"),
                ("Throat Area", f"{geom.throat_area * 1e6:.2f}", "mm^2"),
                ("Contraction Ratio", f"{geom.contraction_ratio:.2f}", ""),
                ("L*", f"{geom.l_star:.3f}", "m"),
                ("Chamber Volume", f"{geom.chamber_volume * 1e6:.2f}", "cm^3"),
            ]
            self.results.set_data(rows)

            # Plot contour
            x, y = generate_chamber_contour(geom)
            self.plot.plot(
                np.array(x) * 1e3, np.array(y) * 1e3,
                xlabel="x [mm]", ylabel="r [mm]",
                title="Chamber Contour (axisymmetric)"
            )
            # Mirror the contour for visual appeal
            self.plot.ax.plot(np.array(x) * 1e3, -np.array(y) * 1e3, color="steelblue", linewidth=1.5)
            self.plot.ax.set_aspect("equal")
            self.plot.figure.tight_layout()
            self.plot._canvas.draw()

            self.log.log(f"Chamber sized: Dt={geom.throat_diameter*1e3:.2f} mm, Dc={geom.chamber_diameter*1e3:.2f} mm")

            # Store for other tabs to use
            self._last_geom = geom
            if self._shared is not None:
                self._shared.update("chamber_geometry", geom)
                self._shared.update("chamber_contour", (x, y))
                self._shared.update("operating_point", {
                    "oxidizer": v["oxidizer"],
                    "fuel": v["fuel"],
                    "mixture_ratio": v["mixture_ratio"],
                    "thrust": v["thrust"],
                    "chamber_pressure": v["chamber_pressure"],
                })

        except Exception as e:
            self.log.log(f"ERROR: {e}")
            self.log.log(traceback.format_exc())
