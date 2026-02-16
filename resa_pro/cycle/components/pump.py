"""Pump component model for RESA Pro cycle analysis.

Models centrifugal or positive-displacement pumps with isentropic
efficiency for pressure-rise calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resa_pro.cycle.components.base import CycleComponent, FluidState


@dataclass
class PumpResult:
    """Pump analysis result."""

    inlet: FluidState
    outlet: FluidState
    pressure_rise: float = 0.0  # Pa
    shaft_power: float = 0.0  # W
    efficiency: float = 0.0
    specific_speed: float = 0.0  # non-dimensional


class Pump(CycleComponent):
    """Centrifugal or positive-displacement pump model.

    Uses isentropic efficiency to compute actual power consumption
    for a given pressure rise.

    Args:
        name: Component name.
        efficiency: Isentropic efficiency (0–1).
    """

    component_type = "pump"

    def __init__(self, name: str = "pump", efficiency: float = 0.65):
        self.name = name
        self._efficiency = efficiency
        self._result: PumpResult | None = None

    def compute(
        self,
        inlet: FluidState,
        outlet_pressure: float = 0.0,
        cp: float = 0.0,
        **kwargs: Any,
    ) -> FluidState:
        """Compute pump outlet state.

        For an incompressible fluid:
            W_ideal = ΔP · ṁ / ρ
            W_actual = W_ideal / η

        The outlet temperature rise is:
            ΔT = W_actual / (ṁ · cp)

        Args:
            inlet: Inlet fluid state.
            outlet_pressure: Required outlet pressure [Pa].
            cp: Specific heat of the fluid [J/(kg·K)]. If 0, uses a
                rough estimate based on density (liquid vs gas).

        Returns:
            Outlet fluid state.
        """
        dp = outlet_pressure - inlet.pressure
        rho = inlet.density if inlet.density > 0 else 1000.0
        mdot = inlet.mass_flow

        # Ideal (isentropic) work per unit mass [J/kg]
        w_ideal = dp / rho
        # Actual work per unit mass
        w_actual = w_ideal / self._efficiency if self._efficiency > 0 else w_ideal

        # Shaft power [W]
        P_shaft = w_actual * mdot

        # Outlet enthalpy
        h_out = inlet.enthalpy + w_actual

        # Temperature rise from absorbed work
        if cp > 0:
            cp_est = cp
        elif rho > 500:
            cp_est = 2000.0  # liquid-like
        else:
            cp_est = 1000.0  # gas-like
        dT = w_actual / cp_est

        outlet = FluidState(
            pressure=outlet_pressure,
            temperature=inlet.temperature + dT,
            mass_flow=mdot,
            density=rho,
            enthalpy=h_out,
            entropy=inlet.entropy,  # approximate
            fluid_name=inlet.fluid_name,
        )

        self._result = PumpResult(
            inlet=inlet,
            outlet=outlet,
            pressure_rise=dp,
            shaft_power=P_shaft,
            efficiency=self._efficiency,
        )

        return outlet

    def power(self) -> float:
        """Shaft power consumed [W] (positive = consumed)."""
        return self._result.shaft_power if self._result else 0.0

    def summary(self) -> dict[str, Any]:
        d = super().summary()
        if self._result:
            d["pressure_rise_bar"] = self._result.pressure_rise / 1e5
            d["efficiency"] = self._result.efficiency
        return d
