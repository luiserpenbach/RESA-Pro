"""Heat exchanger component model for RESA Pro cycle analysis.

Models a counter-flow or co-flow heat exchanger with effectiveness-NTU
method for thermal energy transfer between hot and cold fluid streams.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from resa_pro.cycle.components.base import CycleComponent, FluidState

logger = logging.getLogger(__name__)


@dataclass
class HeatExchangerResult:
    """Heat exchanger analysis result."""

    hot_inlet: FluidState
    hot_outlet: FluidState
    cold_inlet: FluidState
    cold_outlet: FluidState
    heat_transfer: float = 0.0  # W
    effectiveness: float = 0.0
    pressure_drop_hot: float = 0.0  # Pa
    pressure_drop_cold: float = 0.0  # Pa


class HeatExchanger(CycleComponent):
    """Counter-flow heat exchanger using effectiveness-NTU method.

    Models thermal energy transfer between a hot-side and cold-side
    fluid stream, with optional pressure drops on both sides.

    The effectiveness (ε) relates actual heat transfer to the
    thermodynamically maximum possible:
        Q_actual = ε · Q_max
        Q_max = C_min · (T_hot_in - T_cold_in)

    where C_min = min(ṁ_hot · cp_hot, ṁ_cold · cp_cold).

    Args:
        name: Component name.
        effectiveness: Heat exchanger effectiveness (0–1).
        dp_hot: Pressure drop on the hot side [Pa].
        dp_cold: Pressure drop on the cold side [Pa].
    """

    component_type = "heat_exchanger"

    def __init__(
        self,
        name: str = "heat_exchanger",
        effectiveness: float = 0.80,
        dp_hot: float = 50000.0,
        dp_cold: float = 100000.0,
    ):
        self.name = name
        self._effectiveness = effectiveness
        self._dp_hot = dp_hot
        self._dp_cold = dp_cold
        self._result: HeatExchangerResult | None = None

    def compute(
        self,
        inlet: FluidState,
        cold_inlet: FluidState | None = None,
        cp_hot: float = 1500.0,
        cp_cold: float = 2500.0,
        **kwargs: Any,
    ) -> FluidState:
        """Compute heat exchanger outlet states.

        The ``inlet`` parameter is the hot-side inlet (following the
        CycleComponent interface). The cold-side inlet is passed via
        ``cold_inlet``.

        After calling this method, retrieve the cold-side outlet from
        ``self.cold_outlet``.

        Args:
            inlet: Hot-side inlet fluid state.
            cold_inlet: Cold-side inlet fluid state.
            cp_hot: Specific heat of the hot-side fluid [J/(kg·K)].
            cp_cold: Specific heat of the cold-side fluid [J/(kg·K)].

        Returns:
            Hot-side outlet fluid state.
        """
        if cold_inlet is None:
            cold_inlet = FluidState()

        C_hot = inlet.mass_flow * cp_hot
        C_cold = cold_inlet.mass_flow * cp_cold
        C_min = min(C_hot, C_cold)

        # Maximum possible heat transfer [W]
        Q_max = C_min * (inlet.temperature - cold_inlet.temperature)
        Q_actual = self._effectiveness * max(Q_max, 0.0)

        # Temperature changes
        dT_hot = Q_actual / C_hot if C_hot > 0 else 0.0
        dT_cold = Q_actual / C_cold if C_cold > 0 else 0.0

        # Pinch point check: cold outlet must not exceed hot inlet
        T_cold_out = cold_inlet.temperature + dT_cold
        if T_cold_out > inlet.temperature and dT_cold > 0:
            dT_cold = max(inlet.temperature - cold_inlet.temperature, 0.0)
            Q_actual = dT_cold * C_cold if C_cold > 0 else 0.0
            dT_hot = Q_actual / C_hot if C_hot > 0 else 0.0
            logger.warning(
                "HX pinch point: clamped cold outlet to hot inlet temp "
                f"({inlet.temperature:.1f} K)"
            )

        hot_outlet = FluidState(
            pressure=inlet.pressure - self._dp_hot,
            temperature=inlet.temperature - dT_hot,
            mass_flow=inlet.mass_flow,
            density=inlet.density,
            enthalpy=inlet.enthalpy - Q_actual / inlet.mass_flow if inlet.mass_flow > 0 else 0.0,
            fluid_name=inlet.fluid_name,
        )

        cold_outlet = FluidState(
            pressure=cold_inlet.pressure - self._dp_cold,
            temperature=cold_inlet.temperature + dT_cold,
            mass_flow=cold_inlet.mass_flow,
            density=cold_inlet.density,
            enthalpy=cold_inlet.enthalpy + Q_actual / cold_inlet.mass_flow if cold_inlet.mass_flow > 0 else 0.0,
            fluid_name=cold_inlet.fluid_name,
        )

        self._result = HeatExchangerResult(
            hot_inlet=inlet,
            hot_outlet=hot_outlet,
            cold_inlet=cold_inlet,
            cold_outlet=cold_outlet,
            heat_transfer=Q_actual,
            effectiveness=self._effectiveness,
            pressure_drop_hot=self._dp_hot,
            pressure_drop_cold=self._dp_cold,
        )

        return hot_outlet

    @property
    def cold_outlet(self) -> FluidState | None:
        """Cold-side outlet state (available after compute)."""
        return self._result.cold_outlet if self._result else None

    def power(self) -> float:
        """Heat exchangers consume no shaft power."""
        return 0.0

    def summary(self) -> dict[str, Any]:
        d = super().summary()
        if self._result:
            d["heat_transfer_kW"] = self._result.heat_transfer / 1e3
            d["effectiveness"] = self._result.effectiveness
            d["dp_hot_bar"] = self._result.pressure_drop_hot / 1e5
            d["dp_cold_bar"] = self._result.pressure_drop_cold / 1e5
        return d
