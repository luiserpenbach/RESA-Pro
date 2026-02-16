"""Example plugin: Engine mass estimator.

Provides a rough mass estimate for the engine assembly based on
thrust class and chamber pressure using empirical correlations.
"""

from __future__ import annotations

import math
from typing import Any

from resa_pro.plugins.base import Plugin


class MassEstimatorPlugin(Plugin):
    """Rough engine mass estimator based on empirical correlations.

    Uses a simple thrust-to-weight scaling derived from historical
    engine data for small pressure-fed and pump-fed engines.
    """

    name = "mass_estimator"
    version = "0.1.0"
    description = "Estimate dry engine mass from thrust and chamber pressure"
    author = "RESA Pro"

    def calculate(self, engine_state: dict[str, Any]) -> dict[str, Any]:
        """Estimate engine mass.

        Expected keys in engine_state:
            - thrust: Design thrust [N]
            - chamber_pressure: Chamber pressure [Pa]
            - expansion_ratio: Nozzle expansion ratio (optional)

        Returns:
            Dict with estimated masses.
        """
        thrust = engine_state.get("thrust", 2000.0)
        pc = engine_state.get("chamber_pressure", 2e6)
        eps = engine_state.get("expansion_ratio", 10.0)

        # Empirical T/W ratio: higher Pc → lighter chamber per unit thrust
        # Typical range: 30–80 for small engines
        tw_ratio = 40.0 + 20.0 * (2e6 / max(pc, 1e5))

        # Chamber + nozzle mass
        chamber_mass = thrust / (tw_ratio * 9.81)

        # Nozzle mass scales with expansion ratio
        nozzle_factor = 1.0 + 0.1 * math.sqrt(eps)
        total_mass = chamber_mass * nozzle_factor

        # Injector mass ~10% of chamber
        injector_mass = 0.10 * chamber_mass

        return {
            "chamber_mass_kg": round(chamber_mass, 3),
            "nozzle_factor": round(nozzle_factor, 3),
            "injector_mass_kg": round(injector_mass, 3),
            "total_dry_mass_kg": round(total_mass + injector_mass, 3),
            "thrust_to_weight": round(tw_ratio, 1),
        }
