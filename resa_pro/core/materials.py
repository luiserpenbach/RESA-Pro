"""Material property database for RESA Pro.

Loads temperature-dependent material properties from the bundled JSON
database and provides interpolated look-ups.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from resa_pro.utils.interpolation import linear_interp_1d

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_MATERIALS_DB_PATH = _DATA_DIR / "materials.json"


@lru_cache(maxsize=1)
def _load_materials_db() -> dict[str, Any]:
    if not _MATERIALS_DB_PATH.exists():
        logger.warning("Materials database not found at %s", _MATERIALS_DB_PATH)
        return {}
    with open(_MATERIALS_DB_PATH) as f:
        return json.load(f)


def list_materials() -> list[str]:
    """Return all material identifiers in the database."""
    return list(_load_materials_db().keys())


def get_material_info(material_id: str) -> dict[str, Any]:
    """Return the full material record.

    Raises:
        KeyError: If material_id is not in the database.
    """
    db = _load_materials_db()
    for key, val in db.items():
        if key.lower() == material_id.lower():
            return val
    raise KeyError(f"Material '{material_id}' not found. Available: {list(db.keys())}")


class Material:
    """Temperature-dependent material property look-up.

    Args:
        material_id: Identifier matching a key in materials.json.
    """

    def __init__(self, material_id: str):
        info = get_material_info(material_id)
        self.material_id = material_id
        self.name: str = info["name"]
        self.category: str = info["category"]
        self.density: float = info["density"]  # kg/m³
        self.melting_point: float = info["melting_point"]  # K

        # Build interpolation arrays
        k_data = info["thermal_conductivity"]
        self._k_T = np.asarray(k_data["T"], dtype=float)
        self._k_vals = np.asarray(k_data["k"], dtype=float)

        cp_data = info["specific_heat"]
        self._cp_T = np.asarray(cp_data["T"], dtype=float)
        self._cp_vals = np.asarray(cp_data["cp"], dtype=float)

        self.yield_strength_20C: float = info.get("yield_strength_20C", 0.0)  # MPa
        self.ultimate_tensile_20C: float = info.get("ultimate_tensile_20C", 0.0)  # MPa

    def thermal_conductivity(self, T: float) -> float:
        """Thermal conductivity [W/(m·K)] at temperature T [K]."""
        return linear_interp_1d(self._k_T, self._k_vals, T, extrapolate=True)

    def specific_heat(self, T: float) -> float:
        """Specific heat capacity [J/(kg·K)] at temperature T [K]."""
        return linear_interp_1d(self._cp_T, self._cp_vals, T, extrapolate=True)

    def thermal_diffusivity(self, T: float) -> float:
        """Thermal diffusivity [m²/s] at temperature T [K]."""
        k = self.thermal_conductivity(T)
        cp = self.specific_heat(T)
        return k / (self.density * cp)

    def __repr__(self) -> str:
        return f"Material('{self.material_id}': {self.name})"
