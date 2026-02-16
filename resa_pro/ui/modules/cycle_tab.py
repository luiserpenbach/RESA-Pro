"""Cycle analysis tab for RESA Pro GUI."""

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


class CycleTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        splitter = QSplitter()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(splitter)

        # --- Left ---
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        self.form = ParamForm()
        self.form.add_header("Cycle Architecture")
        self.form.add_combo("cycle_type", "Cycle Type", ["pressure_fed", "gas_generator", "expander"], default="pressure_fed")

        self.form.add_separator()
        self.form.add_header("Operating Point")
        self.form.add_float("thrust", "Thrust", 2000.0, unit="N", min_val=10, max_val=1e8, step=100)
        self.form.add_float("pc", "Chamber Pressure", 2e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.form.add_float("mr", "Mixture Ratio", 4.0, min_val=0.5, max_val=20, step=0.1)
        self.form.add_float("c_star", "c*", 1550.0, unit="m/s", min_val=500, max_val=3000, step=10)
        self.form.add_float("gamma", "Gamma", 1.21, min_val=1.05, max_val=1.67, step=0.01)
        self.form.add_float("Tc", "Chamber Temp", 3100.0, unit="K", min_val=500, max_val=5000, step=50)

        self.form.add_separator()
        self.form.add_header("Propellant Properties")
        self.form.add_float("ox_density", "Oxidizer Density", 1220.0, unit="kg/m3", min_val=1, max_val=5000, step=10)
        self.form.add_float("fuel_density", "Fuel Density", 789.0, unit="kg/m3", min_val=1, max_val=5000, step=10)

        self.form.add_separator()
        self.form.add_header("Turbopump (GG/Expander)")
        self.form.add_float("pump_eff", "Pump Efficiency", 0.65, min_val=0.3, max_val=0.95, step=0.01)
        self.form.add_float("turbine_eff", "Turbine Efficiency", 0.60, min_val=0.3, max_val=0.95, step=0.01)
        self.form.add_float("turbine_T_in", "Turbine Inlet Temp", 800.0, unit="K", min_val=300, max_val=2000, step=10)

        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        ll.addWidget(scroll)

        btn = QPushButton("Solve Cycle")
        btn.clicked.connect(self._compute)
        ll.addWidget(btn)

        # --- Right ---
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.results = ResultTable("Cycle Performance")
        rl.addWidget(self.results)

        self.plot = PlotCanvas("Power Balance")
        rl.addWidget(self.plot)

        self.log = LogPanel("Log")
        self.log.setMaximumHeight(100)
        rl.addWidget(self.log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 620])

    def _compute(self) -> None:
        self.log.clear()
        self.results.clear()
        try:
            v = self.form.get_values()
            from resa_pro.cycle.solver import CycleDefinition, CycleType, solve_cycle

            type_map = {
                "pressure_fed": CycleType.PRESSURE_FED,
                "gas_generator": CycleType.GAS_GENERATOR,
                "expander": CycleType.EXPANDER,
            }

            defn = CycleDefinition(
                cycle_type=type_map[v["cycle_type"]],
                thrust=v["thrust"],
                chamber_pressure=v["pc"],
                mixture_ratio=v["mr"],
                c_star=v["c_star"],
                gamma=v["gamma"],
                Tc=v["Tc"],
                ox_density=v["ox_density"],
                fuel_density=v["fuel_density"],
                ox_pump_efficiency=v["pump_eff"],
                fuel_pump_efficiency=v["pump_eff"],
                turbine_efficiency=v["turbine_eff"],
                turbine_inlet_temperature=v["turbine_T_in"],
            )

            result = solve_cycle(defn)

            rows = [
                ("Cycle Type", result.cycle_type.replace("_", " ").title(), ""),
                ("Thrust", f"{result.thrust:.0f}", "N"),
                ("Chamber Pressure", f"{result.chamber_pressure / 1e5:.1f}", "bar"),
                ("Total Mass Flow", f"{result.total_mass_flow:.4f}", "kg/s"),
                ("Mixture Ratio", f"{result.mixture_ratio:.2f}", ""),
                ("Isp (delivered)", f"{result.Isp_delivered:.1f}", "s"),
                ("c*", f"{result.c_star:.0f}", "m/s"),
                ("", "", ""),
                ("Pump Power (total)", f"{result.pump_power_total / 1e3:.2f}", "kW"),
                ("Turbine Power", f"{result.turbine_power_total / 1e3:.2f}", "kW"),
                ("Power Balance Error", f"{result.power_balance_error:.1f}", "W"),
                ("", "", ""),
                ("Ox Tank Pressure", f"{result.tank_pressure_ox / 1e5:.1f}", "bar"),
                ("Fuel Tank Pressure", f"{result.tank_pressure_fuel / 1e5:.1f}", "bar"),
            ]
            self.results.set_data(rows)

            # Power bar chart
            if result.pump_power_total > 0 or result.turbine_power_total > 0:
                labels = ["Pump Power", "Turbine Power"]
                values = [result.pump_power_total / 1e3, result.turbine_power_total / 1e3]
                self.plot.bar(labels, values, ylabel="Power [kW]", title="Power Balance", color="coral")
            else:
                # Pressure budget for pressure-fed
                labels = ["Pc", "Inj dP", "Feed dP", "Valve dP", "Tank P (ox)"]
                pc = result.chamber_pressure / 1e5
                inj_dp = defn.injector_dp_fraction * pc
                feed_dp = defn.ox_feed_line_dp / 1e5
                valve_dp = defn.ox_valve_dp / 1e5
                tank_p = result.tank_pressure_ox / 1e5
                values = [pc, inj_dp, feed_dp, valve_dp, tank_p]
                self.plot.bar(labels, values, ylabel="Pressure [bar]", title="Pressure Budget")

            self.log.log(f"Cycle solved: Isp = {result.Isp_delivered:.1f} s, mdot = {result.total_mass_flow:.4f} kg/s")

        except Exception as e:
            self.log.log(f"ERROR: {e}")
            self.log.log(traceback.format_exc())
