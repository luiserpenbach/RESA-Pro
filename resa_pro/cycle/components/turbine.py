"""Turbine component model for RESA Pro cycle analysis.

Models a gas turbine expanding hot gas through a pressure ratio
with isentropic efficiency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resa_pro.cycle.components.base import CycleComponent, FluidState


@dataclass
class TurbineResult:
    """Turbine analysis result."""

    inlet: FluidState
    outlet: FluidState
    pressure_ratio: float = 0.0  # P_in / P_out
    shaft_power: float = 0.0  # W (positive = produced)
    efficiency: float = 0.0


class Turbine(CycleComponent):
    """Gas turbine model with isentropic efficiency.

    For an ideal gas expanding through a pressure ratio PR:
        T_out_ideal = T_in · (1/PR)^((γ-1)/γ)
        T_out_actual = T_in - η · (T_in - T_out_ideal)
        W = ṁ · cp · (T_in - T_out_actual)

    Args:
        name: Component name.
        efficiency: Isentropic efficiency (0–1).
    """

    component_type = "turbine"

    def __init__(self, name: str = "turbine", efficiency: float = 0.60):
        self.name = name
        self._efficiency = efficiency
        self._result: TurbineResult | None = None

    def compute(
        self,
        inlet: FluidState,
        outlet_pressure: float = 0.0,
        gamma: float = 1.3,
        cp: float = 1500.0,
        **kwargs: Any,
    ) -> FluidState:
        """Compute turbine outlet state.

        Args:
            inlet: Inlet fluid state (hot gas).
            outlet_pressure: Turbine exhaust pressure [Pa].
            gamma: Ratio of specific heats of the working gas.
            cp: Specific heat at constant pressure [J/(kg·K)].

        Returns:
            Outlet fluid state.
        """
        PR = inlet.pressure / outlet_pressure if outlet_pressure > 0 else 1.0

        # Isentropic outlet temperature
        T_out_ideal = inlet.temperature * (1.0 / PR) ** ((gamma - 1.0) / gamma)

        # Actual outlet temperature
        T_out = inlet.temperature - self._efficiency * (inlet.temperature - T_out_ideal)

        # Specific work extracted [J/kg]
        w = cp * (inlet.temperature - T_out)

        # Shaft power [W] (positive = produced)
        P_shaft = w * inlet.mass_flow

        # Outlet density from ideal gas: rho_out = rho_in * (P_out/P_in) * (T_in/T_out)
        if inlet.pressure > 0 and T_out > 0:
            rho_out = inlet.density * (outlet_pressure / inlet.pressure) * (inlet.temperature / T_out)
        else:
            rho_out = inlet.density

        outlet = FluidState(
            pressure=outlet_pressure,
            temperature=T_out,
            mass_flow=inlet.mass_flow,
            density=rho_out,
            enthalpy=inlet.enthalpy - w,
            fluid_name=inlet.fluid_name,
        )

        self._result = TurbineResult(
            inlet=inlet,
            outlet=outlet,
            pressure_ratio=PR,
            shaft_power=P_shaft,
            efficiency=self._efficiency,
        )

        return outlet

    def power(self) -> float:
        """Shaft power produced [W] (negative convention: produced)."""
        return -(self._result.shaft_power) if self._result else 0.0

    def summary(self) -> dict[str, Any]:
        d = super().summary()
        if self._result:
            d["pressure_ratio"] = self._result.pressure_ratio
            d["efficiency"] = self._result.efficiency
            d["shaft_power_kW"] = self._result.shaft_power / 1e3
        return d
