"""Valve and orifice component model for RESA Pro cycle analysis.

Models pressure drops through valves and orifices as either a fixed
pressure drop or a Cv/Kv-based flow coefficient model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resa_pro.cycle.components.base import CycleComponent, FluidState


@dataclass
class ValveResult:
    """Valve analysis result."""

    inlet: FluidState
    outlet: FluidState
    pressure_drop: float = 0.0  # Pa


class Valve(CycleComponent):
    """Simple valve / restriction model.

    Models an isenthalpic pressure drop (throttling).

    Args:
        name: Component name.
        dp: Fixed pressure drop [Pa]. If zero, uses Cv-based model.
        Cv: Flow coefficient [m³/h at 1 bar ΔP] (optional).
    """

    component_type = "valve"

    def __init__(self, name: str = "valve", dp: float = 50000.0, Cv: float | None = None):
        self.name = name
        self._dp_fixed = dp
        self._Cv = Cv
        self._result: ValveResult | None = None

    def compute(self, inlet: FluidState, **kwargs: Any) -> FluidState:
        """Compute valve outlet state (isenthalpic throttling).

        Args:
            inlet: Inlet fluid state.

        Returns:
            Outlet fluid state with reduced pressure.
        """
        if self._Cv is not None and inlet.density > 0:
            # Cv-based: ΔP = (Q / Cv)² · ρ / 1000
            # Q = ṁ / ρ (volumetric flow m³/s)
            Q = inlet.mass_flow / inlet.density  # m³/s
            Q_m3h = Q * 3600.0  # m³/h
            dp = (Q_m3h / self._Cv) ** 2 * (inlet.density / 1000.0) * 1e5
        else:
            dp = self._dp_fixed

        outlet = FluidState(
            pressure=inlet.pressure - dp,
            temperature=inlet.temperature,  # isenthalpic
            mass_flow=inlet.mass_flow,
            density=inlet.density,
            enthalpy=inlet.enthalpy,
            entropy=inlet.entropy,
            fluid_name=inlet.fluid_name,
        )

        self._result = ValveResult(
            inlet=inlet,
            outlet=outlet,
            pressure_drop=dp,
        )

        return outlet

    def power(self) -> float:
        """Valves consume no shaft power."""
        return 0.0

    def summary(self) -> dict[str, Any]:
        d = super().summary()
        if self._result:
            d["pressure_drop_bar"] = self._result.pressure_drop / 1e5
        return d
