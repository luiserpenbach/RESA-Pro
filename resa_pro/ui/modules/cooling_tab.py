"""Cooling & Feed System tab for RESA Pro GUI."""

from __future__ import annotations

import traceback

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


class CoolingFeedTab(QWidget):
    """Combined cooling analysis and feed system sizing tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        tabs = QTabWidget()
        tabs.addTab(self._build_cooling_panel(), "Regen Cooling")
        tabs.addTab(self._build_feed_panel(), "Feed System")
        layout.addWidget(tabs)

    # ---------- Regen Cooling Sub-panel ----------

    def _build_cooling_panel(self) -> QWidget:
        w = QWidget()
        splitter = QSplitter()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        # Left: inputs
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        self.cool_form = ParamForm()
        self.cool_form.add_header("Chamber/Nozzle")
        self.cool_form.add_float("throat_radius", "Throat Radius", 15.0, unit="mm", min_val=1, max_val=500, step=0.5)
        self.cool_form.add_float("pc", "Chamber Pressure", 2e6, unit="Pa", min_val=1e5, max_val=50e6, step=1e5)
        self.cool_form.add_float("Tc", "Chamber Temp", 3100.0, unit="K", min_val=500, max_val=5000, step=50)
        self.cool_form.add_float("gamma", "Gamma", 1.21, min_val=1.05, max_val=1.67, step=0.01)
        self.cool_form.add_float("molar_mass", "Molar Mass", 0.026, unit="kg/mol", min_val=0.001, max_val=0.1, step=0.001)
        self.cool_form.add_float("c_star", "c*", 1550.0, unit="m/s", min_val=500, max_val=3000, step=10)

        self.cool_form.add_separator()
        self.cool_form.add_header("Coolant (Water)")
        self.cool_form.add_float("coolant_mdot", "Coolant Mass Flow", 0.3, unit="kg/s", min_val=0.01, max_val=100, step=0.01)
        self.cool_form.add_float("coolant_T_in", "Inlet Temp", 293.0, unit="K", min_val=200, max_val=500, step=1)
        self.cool_form.add_float("coolant_cp", "Coolant cp", 4180.0, unit="J/(kg.K)", min_val=500, max_val=10000, step=10)
        self.cool_form.add_float("coolant_rho", "Coolant Density", 998.0, unit="kg/m3", min_val=100, max_val=5000, step=1)
        self.cool_form.add_float("coolant_mu", "Coolant Viscosity", 1e-3, unit="Pa.s", min_val=1e-5, max_val=1, decimals=6, step=1e-4)
        self.cool_form.add_float("coolant_k", "Coolant Conductivity", 0.6, unit="W/(m.K)", min_val=0.01, max_val=500, step=0.01)

        self.cool_form.add_separator()
        self.cool_form.add_header("Channel Geometry")
        self.cool_form.add_float("ch_width", "Channel Width", 2.0, unit="mm", min_val=0.2, max_val=20, step=0.1)
        self.cool_form.add_float("ch_height", "Channel Height", 3.0, unit="mm", min_val=0.2, max_val=30, step=0.1)
        self.cool_form.add_float("wall_t", "Wall Thickness", 1.5, unit="mm", min_val=0.2, max_val=10, step=0.1)
        self.cool_form.add_float("fin_w", "Fin Width", 1.5, unit="mm", min_val=0.2, max_val=10, step=0.1)
        self.cool_form.add_float("wall_k", "Wall Conductivity", 390.0, unit="W/(m.K)", min_val=1, max_val=2000, step=1)

        scroll = QScrollArea()
        scroll.setWidget(self.cool_form)
        scroll.setWidgetResizable(True)
        ll.addWidget(scroll)

        btn = QPushButton("Analyze Cooling")
        btn.clicked.connect(self._compute_cooling)
        ll.addWidget(btn)

        # Right: results
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.cool_results = ResultTable("Cooling Analysis")
        rl.addWidget(self.cool_results)
        self.cool_plot = PlotCanvas("Wall Temperature")
        rl.addWidget(self.cool_plot)
        self.cool_log = LogPanel("Log")
        self.cool_log.setMaximumHeight(80)
        rl.addWidget(self.cool_log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 620])
        return w

    # ---------- Feed System Sub-panel ----------

    def _build_feed_panel(self) -> QWidget:
        w = QWidget()
        splitter = QSplitter()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        self.feed_form = ParamForm()
        self.feed_form.add_header("Tank Sizing")
        self.feed_form.add_float("prop_mass", "Propellant Mass", 5.0, unit="kg", min_val=0.1, max_val=10000, step=0.5)
        self.feed_form.add_float("prop_density", "Propellant Density", 789.0, unit="kg/m3", min_val=100, max_val=5000, step=10)
        self.feed_form.add_float("tank_pressure", "Tank Pressure", 3e6, unit="Pa", min_val=1e5, max_val=100e6, step=1e5)
        self.feed_form.add_float("tank_diameter", "Tank Inner Diameter", 0.15, unit="m", min_val=0.01, max_val=5, step=0.01)
        self.feed_form.add_float("mat_yield", "Material Yield Strength", 276e6, unit="Pa", min_val=1e6, max_val=2e9, step=1e6)
        self.feed_form.add_float("mat_density", "Material Density", 2700.0, unit="kg/m3", min_val=500, max_val=20000, step=10)
        self.feed_form.add_float("safety_factor", "Safety Factor", 2.0, min_val=1.0, max_val=5.0, step=0.1)

        self.feed_form.add_separator()
        self.feed_form.add_header("Pressurant (Blowdown)")
        self.feed_form.add_float("press_gamma", "Pressurant Gamma", 1.4, min_val=1.0, max_val=1.67, step=0.01)
        self.feed_form.add_float("press_molar", "Pressurant Molar Mass", 0.028, unit="kg/mol", min_val=0.002, max_val=0.05, step=0.001)
        self.feed_form.add_float("press_temp", "Pressurant Temp", 293.0, unit="K", min_val=200, max_val=500, step=1)
        self.feed_form.add_float("blowdown_ratio", "Blowdown Ratio", 3.0, min_val=1.5, max_val=10, step=0.1)

        scroll = QScrollArea()
        scroll.setWidget(self.feed_form)
        scroll.setWidgetResizable(True)
        ll.addWidget(scroll)

        btn_tank = QPushButton("Size Tank")
        btn_tank.clicked.connect(self._compute_tank)
        ll.addWidget(btn_tank)

        btn_press = QPushButton("Size Pressurant")
        btn_press.setProperty("secondary", True)
        btn_press.clicked.connect(self._compute_pressurant)
        ll.addWidget(btn_press)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.feed_results = ResultTable("Feed System")
        rl.addWidget(self.feed_results)
        self.feed_plot = PlotCanvas("System")
        rl.addWidget(self.feed_plot)
        self.feed_log = LogPanel("Log")
        self.feed_log.setMaximumHeight(80)
        rl.addWidget(self.feed_log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 620])
        return w

    # ---------- Callbacks ----------

    def _compute_cooling(self) -> None:
        self.cool_log.clear()
        self.cool_results.clear()
        try:
            v = self.cool_form.get_values()
            from resa_pro.core.chamber import size_chamber_from_dimensions, generate_chamber_contour
            from resa_pro.core.nozzle import parabolic_nozzle
            from resa_pro.core.cooling import analyze_regen_cooling

            throat_r = v["throat_radius"] / 1e3
            geom = size_chamber_from_dimensions(throat_diameter=throat_r * 2, contraction_ratio=3.0, l_star=1.2)
            cx, cy = generate_chamber_contour(geom)
            noz = parabolic_nozzle(throat_r, expansion_ratio=5.0)
            full_x = list(cx) + [x + cx[-1] for x in noz.x[1:]]
            full_y = list(cy) + list(noz.y[1:])

            result = analyze_regen_cooling(
                contour_x=full_x, contour_y=full_y, throat_radius=throat_r,
                pc=v["pc"], c_star=v["c_star"], Tc=v["Tc"],
                gamma=v["gamma"], molar_mass=v["molar_mass"],
                coolant_mass_flow=v["coolant_mdot"], coolant_inlet_temp=v["coolant_T_in"],
                coolant_cp=v["coolant_cp"], coolant_rho=v["coolant_rho"],
                coolant_mu=v["coolant_mu"], coolant_k=v["coolant_k"],
                wall_conductivity=v["wall_k"],
                channel_width=v["ch_width"] / 1e3, channel_height=v["ch_height"] / 1e3,
                wall_thickness=v["wall_t"] / 1e3, fin_width=v["fin_w"] / 1e3,
            )

            rows = [
                ("Max Wall Temperature", f"{result.max_wall_temperature:.0f}", "K"),
                ("Max Heat Flux", f"{result.max_heat_flux / 1e6:.2f}", "MW/m^2"),
                ("Total Heat Load", f"{result.total_heat_load / 1e3:.2f}", "kW"),
                ("Coolant Outlet Temp", f"{result.coolant_outlet_temperature:.1f}", "K"),
                ("Total Pressure Drop", f"{result.total_pressure_drop / 1e5:.2f}", "bar"),
                ("Stations", f"{len(result.stations)}", ""),
            ]
            self.cool_results.set_data(rows)

            x_arr = [s.x * 1e3 for s in result.stations]
            tw_arr = [s.T_wg for s in result.stations]
            tc_arr = [s.T_coolant for s in result.stations]

            self.cool_plot.plot_multi(
                [(x_arr, tw_arr, "T_wall (gas side)"), (x_arr, tc_arr, "T_coolant")],
                xlabel="x [mm]", ylabel="T [K]",
                title="Temperature Distribution",
            )
            self.cool_log.log(f"Max Tw = {result.max_wall_temperature:.0f} K, Total Q = {result.total_heat_load/1e3:.1f} kW")

        except Exception as e:
            self.cool_log.log(f"ERROR: {e}")
            self.cool_log.log(traceback.format_exc())

    def _compute_tank(self) -> None:
        self.feed_log.clear()
        self.feed_results.clear()
        try:
            v = self.feed_form.get_values()
            from resa_pro.core.feed_system import size_tank

            tank = size_tank(
                propellant_mass=v["prop_mass"],
                propellant_density=v["prop_density"],
                tank_pressure=v["tank_pressure"],
                inner_diameter=v["tank_diameter"],
                material_yield_strength=v["mat_yield"],
                material_density=v["mat_density"],
                safety_factor=v["safety_factor"],
            )

            rows = [
                ("Propellant Volume", f"{tank.propellant_volume * 1e3:.3f}", "L"),
                ("Total Volume", f"{tank.total_volume * 1e3:.3f}", "L"),
                ("Cylinder Length", f"{tank.cylinder_length * 1e3:.1f}", "mm"),
                ("Wall Thickness", f"{tank.wall_thickness * 1e3:.2f}", "mm"),
                ("Tank Mass", f"{tank.tank_mass:.3f}", "kg"),
                ("Tank Pressure", f"{tank.tank_pressure / 1e5:.1f}", "bar"),
            ]
            self.feed_results.set_data(rows)

            labels = ["Propellant", "Tank", "Total"]
            vals = [v["prop_mass"], tank.tank_mass, v["prop_mass"] + tank.tank_mass]
            self.feed_plot.bar(labels, vals, ylabel="Mass [kg]", title="Mass Breakdown")

            self.feed_log.log(f"Tank: {tank.tank_mass:.3f} kg, wall {tank.wall_thickness*1e3:.2f} mm")

        except Exception as e:
            self.feed_log.log(f"ERROR: {e}")
            self.feed_log.log(traceback.format_exc())

    def _compute_pressurant(self) -> None:
        self.feed_log.clear()
        try:
            v = self.feed_form.get_values()
            from resa_pro.core.feed_system import size_tank, size_pressurant_blowdown

            tank = size_tank(
                propellant_mass=v["prop_mass"],
                propellant_density=v["prop_density"],
                tank_pressure=v["tank_pressure"],
                inner_diameter=v["tank_diameter"],
                material_yield_strength=v["mat_yield"],
                material_density=v["mat_density"],
                safety_factor=v["safety_factor"],
            )

            press = size_pressurant_blowdown(
                tank_volume=tank.total_volume,
                tank_pressure=v["tank_pressure"],
                pressurant_gamma=v["press_gamma"],
                pressurant_molar_mass=v["press_molar"],
                pressurant_temperature=v["press_temp"],
                blowdown_ratio=v["blowdown_ratio"],
            )

            self.feed_results.clear()
            rows = [
                ("Pressurant Mass", f"{press.pressurant_mass:.4f}", "kg"),
                ("Bottle Volume", f"{press.bottle_volume * 1e3:.3f}", "L"),
                ("Initial Bottle Pressure", f"{press.bottle_pressure_initial / 1e5:.1f}", "bar"),
                ("Final Bottle Pressure", f"{press.bottle_pressure_final / 1e5:.1f}", "bar"),
                ("Blowdown Ratio", f"{press.blowdown_ratio:.1f}", ""),
            ]
            self.feed_results.set_data(rows)
            self.feed_log.log(f"Pressurant: {press.pressurant_mass:.4f} kg, bottle {press.bottle_volume*1e3:.2f} L")

        except Exception as e:
            self.feed_log.log(f"ERROR: {e}")
            self.feed_log.log(traceback.format_exc())
