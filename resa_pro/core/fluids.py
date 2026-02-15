"""Fluid property interface wrapping CoolProp.

Provides a convenient, cached interface to thermodynamic properties with
proper error handling and optional RefProp backend fallback.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI

logger = logging.getLogger(__name__)

# Path to bundled propellant database
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_PROPELLANT_DB_PATH = _DATA_DIR / "propellants.json"

# CoolProp input pairs
_INPUT_PAIRS = {
    ("T", "P"): CP.PT_INPUTS,
    ("P", "T"): CP.PT_INPUTS,
    ("P", "H"): CP.HmassP_INPUTS,
    ("H", "P"): CP.HmassP_INPUTS,
    ("P", "S"): CP.PSmass_INPUTS,
    ("P", "Q"): CP.PQ_INPUTS,
    ("T", "Q"): CP.QT_INPUTS,
}


class FluidPropertyError(Exception):
    """Raised when a fluid property calculation fails."""


class Fluid:
    """Interface to thermodynamic properties of a single fluid.

    Wraps CoolProp's low-level AbstractState for efficiency and caches the
    backend object.  Supports both HEOS (CoolProp default) and REFPROP
    backends transparently.

    Args:
        name: CoolProp fluid name (e.g. "NitrousOxide", "Ethanol", "Oxygen").
        backend: CoolProp backend string.  ``"HEOS"`` for built-in,
                 ``"REFPROP"`` if RefProp is installed.
    """

    def __init__(self, name: str, backend: str = "HEOS"):
        self.name = name
        self.backend = backend
        try:
            self._state = CP.AbstractState(backend, name)
        except Exception as exc:
            raise FluidPropertyError(
                f"Cannot create fluid '{name}' with backend '{backend}': {exc}"
            ) from exc

        # Cache critical point
        self.T_critical = self._state.T_critical()
        self.P_critical = self._state.p_critical()
        self.T_min = self._state.Tmin()
        self.molar_mass = self._state.molar_mass()  # kg/mol

    # --- Core property access ---

    def _update(self, input_pair: int, val1: float, val2: float) -> None:
        """Update the internal state; raise FluidPropertyError on failure."""
        try:
            self._state.update(input_pair, val1, val2)
        except Exception as exc:
            raise FluidPropertyError(f"State update failed for {self.name}: {exc}") from exc

    def props_at_TP(self, T: float, P: float) -> dict[str, float]:
        """Return a property bundle at given temperature [K] and pressure [Pa]."""
        self._update(CP.PT_INPUTS, P, T)
        return self._extract_props()

    def props_at_PH(self, P: float, H: float) -> dict[str, float]:
        """Return a property bundle at given pressure [Pa] and enthalpy [J/kg]."""
        self._update(CP.HmassP_INPUTS, H, P)
        return self._extract_props()

    def _extract_props(self) -> dict[str, float]:
        s = self._state
        return {
            "T": s.T(),
            "P": s.p(),
            "rho": s.rhomass(),
            "h": s.hmass(),
            "s": s.smass(),
            "cp": s.cpmass(),
            "cv": s.cvmass(),
            "mu": s.viscosity(),
            "k": s.conductivity(),
            "phase": s.phase(),
            "Q": s.Q() if s.phase() in (CP.iphase_twophase,) else -1.0,
            "speed_of_sound": s.speed_sound(),
        }

    # --- Convenience scalar lookups ---

    def density(self, T: float, P: float) -> float:
        """Density [kg/m³] at T [K], P [Pa]."""
        return PropsSI("D", "T", T, "P", P, self.name)

    def specific_heat_cp(self, T: float, P: float) -> float:
        """Isobaric specific heat [J/(kg·K)]."""
        return PropsSI("C", "T", T, "P", P, self.name)

    def viscosity(self, T: float, P: float) -> float:
        """Dynamic viscosity [Pa·s]."""
        return PropsSI("V", "T", T, "P", P, self.name)

    def thermal_conductivity(self, T: float, P: float) -> float:
        """Thermal conductivity [W/(m·K)]."""
        return PropsSI("L", "T", T, "P", P, self.name)

    def enthalpy(self, T: float, P: float) -> float:
        """Mass-specific enthalpy [J/kg]."""
        return PropsSI("H", "T", T, "P", P, self.name)

    def entropy(self, T: float, P: float) -> float:
        """Mass-specific entropy [J/(kg·K)]."""
        return PropsSI("S", "T", T, "P", P, self.name)

    def speed_of_sound(self, T: float, P: float) -> float:
        """Speed of sound [m/s]."""
        return PropsSI("A", "T", T, "P", P, self.name)

    def gamma(self, T: float, P: float) -> float:
        """Ratio of specific heats cp/cv."""
        cp = self.specific_heat_cp(T, P)
        cv = PropsSI("O", "T", T, "P", P, self.name)  # Cv
        return cp / cv

    def saturation_pressure(self, T: float) -> float:
        """Saturation (vapour) pressure [Pa] at temperature T [K]."""
        return PropsSI("P", "T", T, "Q", 0, self.name)

    def saturation_temperature(self, P: float) -> float:
        """Saturation temperature [K] at pressure P [Pa]."""
        return PropsSI("T", "P", P, "Q", 0, self.name)

    def quality(self, P: float, H: float) -> float:
        """Vapour quality at given P [Pa] and H [J/kg]. Returns -1 if single-phase."""
        try:
            return PropsSI("Q", "P", P, "H", H, self.name)
        except Exception:
            return -1.0

    def __repr__(self) -> str:
        return f"Fluid('{self.name}', backend='{self.backend}')"


# --- Propellant database ---


@lru_cache(maxsize=1)
def _load_propellant_db() -> dict[str, Any]:
    """Load the propellant database JSON file."""
    if not _PROPELLANT_DB_PATH.exists():
        logger.warning("Propellant database not found at %s", _PROPELLANT_DB_PATH)
        return {}
    with open(_PROPELLANT_DB_PATH) as f:
        return json.load(f)


def list_propellants() -> list[str]:
    """Return names of all propellants in the database."""
    return list(_load_propellant_db().keys())


def get_propellant_info(name: str) -> dict[str, Any]:
    """Get propellant metadata from the database.

    Args:
        name: Propellant name (case-insensitive lookup).

    Returns:
        Dictionary with propellant properties.

    Raises:
        KeyError: If propellant is not found.
    """
    db = _load_propellant_db()
    # Case-insensitive lookup
    for key, val in db.items():
        if key.lower() == name.lower():
            return val
    raise KeyError(f"Propellant '{name}' not found. Available: {list(db.keys())}")


def get_fluid(propellant_name: str) -> Fluid:
    """Create a Fluid instance from a propellant database entry.

    Args:
        propellant_name: Name as it appears in propellants.json.

    Returns:
        Fluid instance configured for the propellant.
    """
    info = get_propellant_info(propellant_name)
    coolprop_name = info.get("coolprop_name", propellant_name)
    backend = info.get("backend", "HEOS")
    return Fluid(coolprop_name, backend=backend)
