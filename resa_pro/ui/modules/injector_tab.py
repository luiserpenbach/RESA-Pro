"""Injector design tab for RESA Pro GUI."""

from __future__ import annotations

import traceback

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


class InjectorTab(QWidget):
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
        self.form.add_header("Flow Conditions")
        self.form.add_float("mass_flow", "Total Mass Flow", 1.0, unit="kg/s", min_val=0.01, max_val=1000, step=0.05)
        self.form.add_float("mixture_ratio", "Mixture Ratio (O/F)", 4.0, min_val=0.5, max_val=20, step=0.1)
        self.form.add_float("chamber_pressure", "Chamber Pressure", 2e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)

        self.form.add_separator()
        self.form.add_header("Propellant Properties")
        self.form.add_float("rho_ox", "Oxidizer Density", 1220.0, unit="kg/m3", min_val=1, max_val=5000, step=10)
        self.form.add_float("rho_fuel", "Fuel Density", 789.0, unit="kg/m3", min_val=1, max_val=5000, step=10)

        self.form.add_separator()
        self.form.add_header("Injector Design")
        self.form.add_float("dp_fraction", "dP / Pc Fraction", 0.15, min_val=0.05, max_val=0.40, step=0.01)
        self.form.add_int("n_elements_ox", "Ox Elements", 12, min_val=1, max_val=500)
        self.form.add_int("n_elements_fuel", "Fuel Elements", 12, min_val=1, max_val=500)
        self.form.add_float("cd_ox", "Cd (Oxidizer)", 0.65, min_val=0.3, max_val=1.0, step=0.01)
        self.form.add_float("cd_fuel", "Cd (Fuel)", 0.65, min_val=0.3, max_val=1.0, step=0.01)

        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        left_layout.addWidget(scroll)

        btn = QPushButton("Design Injector")
        btn.clicked.connect(self._compute)
        left_layout.addWidget(btn)

        # --- Right ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.results = ResultTable("Injector Design")
        right_layout.addWidget(self.results)

        self.plot = PlotCanvas("Pressure Drops")
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
            from resa_pro.core.injector import design_injector

            design = design_injector(
                mass_flow=v["mass_flow"],
                mixture_ratio=v["mixture_ratio"],
                chamber_pressure=v["chamber_pressure"],
                rho_oxidizer=v["rho_ox"],
                rho_fuel=v["rho_fuel"],
                dp_fraction=v["dp_fraction"],
                n_elements_ox=v["n_elements_ox"],
                n_elements_fuel=v["n_elements_fuel"],
                cd_ox=v["cd_ox"],
                cd_fuel=v["cd_fuel"],
            )

            rows = [
                ("Ox Mass Flow", f"{design.mass_flow_oxidizer:.4f}", "kg/s"),
                ("Fuel Mass Flow", f"{design.mass_flow_fuel:.4f}", "kg/s"),
                ("Ox dP", f"{design.dp_oxidizer / 1e5:.2f}", "bar"),
                ("Fuel dP", f"{design.dp_fuel / 1e5:.2f}", "bar"),
                ("Ox Elements", f"{design.n_elements_ox}", ""),
                ("Fuel Elements", f"{design.n_elements_fuel}", ""),
                ("Ox Orifice Diameter", f"{design.element_ox.diameter * 1e3:.3f}", "mm"),
                ("Fuel Orifice Diameter", f"{design.element_fuel.diameter * 1e3:.3f}", "mm"),
                ("Ox Velocity", f"{design.element_ox.velocity:.1f}", "m/s"),
                ("Fuel Velocity", f"{design.element_fuel.velocity:.1f}", "m/s"),
                ("Momentum Ratio", f"{design.momentum_ratio:.3f}", ""),
            ]
            self.results.set_data(rows)

            # Bar chart of pressure drops
            labels = ["Ox dP", "Fuel dP", "Pc"]
            values = [design.dp_oxidizer / 1e5, design.dp_fuel / 1e5, v["chamber_pressure"] / 1e5]
            self.plot.bar(labels, values, ylabel="Pressure [bar]", title="Injector Pressure Budget")

            self.log.log(f"Injector designed: {design.n_elements_ox} ox + {design.n_elements_fuel} fuel elements")

        except Exception as e:
            self.log.log(f"ERROR: {e}")
            self.log.log(traceback.format_exc())
