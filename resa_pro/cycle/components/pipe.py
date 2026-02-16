"""Pipe / feed line component model for RESA Pro cycle analysis.

Wraps the feed_system.feed_line_pressure_drop function into the
cycle component interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resa_pro.core.feed_system import feed_line_pressure_drop
from resa_pro.cycle.components.base import CycleComponent, FluidState


@dataclass
class PipeResult:
    """Pipe analysis result."""

    inlet: FluidState
    outlet: FluidState
    pressure_drop: float = 0.0  # Pa
    velocity: float = 0.0  # m/s
    reynolds: float = 0.0


class Pipe(CycleComponent):
    """Feed line / pipe segment model.

    Computes friction + minor losses + hydrostatic pressure drop.

    Args:
        name: Component name.
        diameter: Inner diameter [m].
        length: Pipe length [m].
        height_change: Elevation change [m] (positive = upward).
        K_minor: Sum of minor loss coefficients.
        roughness: Surface roughness [m].
    """

    component_type = "pipe"

    def __init__(
        self,
        name: str = "pipe",
        diameter: float = 0.012,
        length: float = 1.0,
        height_change: float = 0.0,
        K_minor: float = 5.0,
        roughness: float = 1.5e-6,
    ):
        self.name = name
        self._diameter = diameter
        self._length = length
        self._height_change = height_change
        self._K_minor = K_minor
        self._roughness = roughness
        self._result: PipeResult | None = None

    def compute(self, inlet: FluidState, mu: float = 1e-3, **kwargs: Any) -> FluidState:
        """Compute pipe outlet state.

        Args:
            inlet: Inlet fluid state.
            mu: Dynamic viscosity [Pa·s].

        Returns:
            Outlet fluid state with reduced pressure.
        """
        rho = inlet.density if inlet.density > 0 else 1000.0

        fl = feed_line_pressure_drop(
            mass_flow=inlet.mass_flow,
            rho=rho,
            mu=mu,
            line_diameter=self._diameter,
            line_length=self._length,
            height_change=self._height_change,
            K_minor=self._K_minor,
            roughness=self._roughness,
        )

        outlet = FluidState(
            pressure=inlet.pressure - fl.total_dp,
            temperature=inlet.temperature,
            mass_flow=inlet.mass_flow,
            density=rho,
            enthalpy=inlet.enthalpy,
            fluid_name=inlet.fluid_name,
        )

        self._result = PipeResult(
            inlet=inlet,
            outlet=outlet,
            pressure_drop=fl.total_dp,
            velocity=fl.velocity,
            reynolds=fl.reynolds,
        )

        return outlet

    def power(self) -> float:
        """Pipes consume no shaft power."""
        return 0.0

    def summary(self) -> dict[str, Any]:
        d = super().summary()
        if self._result:
            d["pressure_drop_bar"] = self._result.pressure_drop / 1e5
            d["velocity_m_s"] = self._result.velocity
            d["reynolds"] = self._result.reynolds
        return d
