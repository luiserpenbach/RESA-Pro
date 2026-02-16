"""Nozzle design tab for RESA Pro GUI."""

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


class NozzleTab(QWidget):
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
        self.form.add_header("Nozzle Parameters")
        self.form.add_float("throat_radius", "Throat Radius", 15.0, unit="mm", min_val=0.5, max_val=500, step=0.5)
        self.form.add_float("expansion_ratio", "Expansion Ratio", 10.0, min_val=1.1, max_val=300, step=0.5)
        self.form.add_combo("method", "Nozzle Type", ["parabolic", "conical"], default="parabolic")

        self.form.add_separator()
        self.form.add_header("Conical Options")
        self.form.add_float("half_angle", "Half Angle", 15.0, unit="deg", min_val=5, max_val=30, step=0.5)

        self.form.add_separator()
        self.form.add_header("Parabolic Options")
        self.form.add_float("frac_length", "Fractional Length", 0.8, min_val=0.5, max_val=1.0, step=0.05)

        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        left_layout.addWidget(scroll)

        btn = QPushButton("Design Nozzle")
        btn.clicked.connect(self._compute)
        left_layout.addWidget(btn)

        # --- Right: results ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.results = ResultTable("Nozzle Geometry")
        right_layout.addWidget(self.results)

        self.plot = PlotCanvas("Nozzle Contour")
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
            throat_r = v["throat_radius"] / 1e3  # mm → m

            if v["method"] == "conical":
                from resa_pro.core.nozzle import conical_nozzle
                contour = conical_nozzle(
                    throat_radius=throat_r,
                    expansion_ratio=v["expansion_ratio"],
                    half_angle=v["half_angle"],
                )
            else:
                from resa_pro.core.nozzle import parabolic_nozzle
                contour = parabolic_nozzle(
                    throat_radius=throat_r,
                    expansion_ratio=v["expansion_ratio"],
                    fractional_length=v["frac_length"],
                )

            rows = [
                ("Method", v["method"].title(), ""),
                ("Throat Radius", f"{contour.throat_radius * 1e3:.2f}", "mm"),
                ("Exit Radius", f"{contour.exit_radius * 1e3:.2f}", "mm"),
                ("Length", f"{contour.length * 1e3:.2f}", "mm"),
                ("Expansion Ratio", f"{contour.expansion_ratio:.2f}", ""),
                ("Exit Area", f"{contour.exit_area * 1e6:.1f}", "mm^2"),
            ]
            self.results.set_data(rows)

            # Plot contour
            x = np.array(contour.x) * 1e3
            y = np.array(contour.y) * 1e3
            self.plot.ax.clear()
            self.plot.ax.plot(x, y, color="steelblue", linewidth=1.5)
            self.plot.ax.plot(x, -y, color="steelblue", linewidth=1.5)
            self.plot.ax.set_xlabel("x [mm]", fontsize=9)
            self.plot.ax.set_ylabel("r [mm]", fontsize=9)
            self.plot.ax.set_title(f"{v['method'].title()} Nozzle Contour", fontsize=10)
            self.plot.ax.set_aspect("equal")
            self.plot.ax.grid(True, alpha=0.3)
            self.plot.figure.tight_layout()
            self.plot._canvas.draw()

            self.log.log(f"Nozzle designed: L={contour.length*1e3:.1f} mm, Re={contour.exit_radius*1e3:.1f} mm")

            self._last_contour = contour

        except Exception as e:
            self.log.log(f"ERROR: {e}")
            self.log.log(traceback.format_exc())
