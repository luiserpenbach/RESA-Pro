"""Base classes for cycle components.

Defines the common interface for all thermodynamic cycle components
(pumps, turbines, valves, heat exchangers, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FluidState:
    """Thermodynamic state of a fluid at a point in the cycle.

    All properties in SI units.
    """

    pressure: float = 0.0  # Pa
    temperature: float = 0.0  # K
    mass_flow: float = 0.0  # kg/s
    density: float = 0.0  # kg/m³
    enthalpy: float = 0.0  # J/kg
    entropy: float = 0.0  # J/(kg·K)
    quality: float = -1.0  # vapour quality (-1 = subcooled/superheated)
    fluid_name: str = ""

    @property
    def is_two_phase(self) -> bool:
        return 0.0 <= self.quality <= 1.0


class CycleComponent(ABC):
    """Abstract base class for a cycle component.

    Every component takes one or more inlet FluidStates and produces
    one or more outlet FluidStates, along with power and performance
    metrics.
    """

    name: str = ""
    component_type: str = ""

    @abstractmethod
    def compute(self, inlet: FluidState, **kwargs: Any) -> FluidState:
        """Run the component model.

        Args:
            inlet: Inlet fluid state.
            **kwargs: Component-specific parameters.

        Returns:
            Outlet fluid state.
        """
        ...

    @abstractmethod
    def power(self) -> float:
        """Net power [W] consumed (positive) or produced (negative)."""
        ...

    def summary(self) -> dict[str, Any]:
        """Return a summary dictionary of the component state."""
        return {
            "name": self.name,
            "type": self.component_type,
            "power_W": self.power(),
        }
