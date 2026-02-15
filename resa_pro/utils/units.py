"""Unit conversion utilities for RESA Pro.

Provides a lightweight unit conversion system built on top of pint,
with convenience functions for common rocket engine quantities.
"""

from __future__ import annotations

from functools import lru_cache

import pint

# Module-level unit registry (singleton)
_ureg = pint.UnitRegistry()
_ureg.default_format = "~P"  # short pretty format


def get_unit_registry() -> pint.UnitRegistry:
    """Return the shared pint UnitRegistry instance."""
    return _ureg


Q_ = _ureg.Quantity


# --- Convenience conversion functions ---


def pressure_to_si(value: float, unit: str) -> float:
    """Convert pressure value to Pascals.

    Args:
        value: Numeric pressure value.
        unit: Source unit string (e.g. "bar", "psi", "MPa", "atm").

    Returns:
        Pressure in Pa.
    """
    return Q_(value, unit).to("Pa").magnitude


def pressure_from_si(value_pa: float, unit: str) -> float:
    """Convert pressure from Pascals to target unit."""
    return Q_(value_pa, "Pa").to(unit).magnitude


def temperature_to_si(value: float, unit: str) -> float:
    """Convert temperature to Kelvin.

    Args:
        value: Numeric temperature value.
        unit: Source unit string (e.g. "degC", "degF", "degR").

    Returns:
        Temperature in K.
    """
    return Q_(value, unit).to("K").magnitude


def temperature_from_si(value_k: float, unit: str) -> float:
    """Convert temperature from Kelvin to target unit."""
    return Q_(value_k, "K").to(unit).magnitude


def length_to_si(value: float, unit: str) -> float:
    """Convert length to meters."""
    return Q_(value, unit).to("m").magnitude


def length_from_si(value_m: float, unit: str) -> float:
    """Convert length from meters to target unit."""
    return Q_(value_m, "m").to(unit).magnitude


def mass_flow_to_si(value: float, unit: str) -> float:
    """Convert mass flow rate to kg/s."""
    return Q_(value, unit).to("kg/s").magnitude


def force_to_si(value: float, unit: str) -> float:
    """Convert force to Newtons."""
    return Q_(value, unit).to("N").magnitude


def velocity_to_si(value: float, unit: str) -> float:
    """Convert velocity to m/s."""
    return Q_(value, unit).to("m/s").magnitude


@lru_cache(maxsize=256)
def convert(value: float, from_unit: str, to_unit: str) -> float:
    """General-purpose unit conversion.

    Args:
        value: Numeric value in *from_unit*.
        from_unit: Source unit string.
        to_unit: Target unit string.

    Returns:
        Converted numeric value.
    """
    return Q_(value, from_unit).to(to_unit).magnitude
