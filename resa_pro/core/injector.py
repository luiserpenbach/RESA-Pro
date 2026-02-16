"""Injector design module for RESA Pro.

Provides sizing of injection elements (orifices) for liquid-propellant
rocket engines, including pressure drop calculations, element count
estimation, and basic spray characterisation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from resa_pro.utils.constants import PI


@dataclass
class InjectorElement:
    """Single injection element (orifice) specification."""

    diameter: float = 0.0  # m — orifice diameter
    area: float = 0.0  # m² — orifice area
    cd: float = 0.65  # discharge coefficient
    velocity: float = 0.0  # m/s — injection velocity


@dataclass
class InjectorDesign:
    """Complete injector design result."""

    # Operating conditions
    mass_flow_oxidizer: float = 0.0  # kg/s
    mass_flow_fuel: float = 0.0  # kg/s
    mixture_ratio: float = 0.0  # O/F
    chamber_pressure: float = 0.0  # Pa

    # Pressure drops
    dp_oxidizer: float = 0.0  # Pa — oxidizer pressure drop
    dp_fuel: float = 0.0  # Pa — fuel pressure drop
    dp_fraction_ox: float = 0.0  # fraction of Pc
    dp_fraction_fuel: float = 0.0  # fraction of Pc

    # Oxidizer side
    n_elements_ox: int = 0
    element_ox: InjectorElement = None  # type: ignore[assignment]

    # Fuel side
    n_elements_fuel: int = 0
    element_fuel: InjectorElement = None  # type: ignore[assignment]

    # Manifold pressures
    manifold_pressure_ox: float = 0.0  # Pa
    manifold_pressure_fuel: float = 0.0  # Pa

    # Spray characterisation
    momentum_ratio: float = 0.0  # oxidizer/fuel momentum ratio


def orifice_mass_flow(
    cd: float,
    area: float,
    dp: float,
    rho: float,
) -> float:
    """Mass flow rate through a single orifice [kg/s].

    Uses the standard incompressible orifice equation:
        ṁ = Cd · A · √(2 · ρ · ΔP)

    Args:
        cd: Discharge coefficient (typically 0.6–0.8).
        area: Orifice cross-sectional area [m²].
        dp: Pressure drop across orifice [Pa].
        rho: Upstream fluid density [kg/m³].

    Returns:
        Mass flow rate [kg/s].
    """
    return cd * area * math.sqrt(2.0 * rho * dp)


def orifice_area_from_flow(
    mass_flow: float,
    cd: float,
    dp: float,
    rho: float,
) -> float:
    """Required total orifice area for a given mass flow [m²].

    Args:
        mass_flow: Required mass flow rate [kg/s].
        cd: Discharge coefficient.
        dp: Pressure drop across orifice [Pa].
        rho: Upstream fluid density [kg/m³].

    Returns:
        Total orifice area [m²].
    """
    return mass_flow / (cd * math.sqrt(2.0 * rho * dp))


def injection_velocity(cd: float, dp: float, rho: float) -> float:
    """Injection velocity through an orifice [m/s].

    v = Cd · √(2 · ΔP / ρ)

    Args:
        cd: Discharge coefficient.
        dp: Pressure drop [Pa].
        rho: Fluid density [kg/m³].

    Returns:
        Injection velocity [m/s].
    """
    return cd * math.sqrt(2.0 * dp / rho)


def design_injector(
    mass_flow: float,
    mixture_ratio: float,
    chamber_pressure: float,
    rho_oxidizer: float,
    rho_fuel: float,
    dp_fraction: float = 0.20,
    dp_fraction_ox: float | None = None,
    dp_fraction_fuel: float | None = None,
    cd_ox: float = 0.65,
    cd_fuel: float = 0.65,
    element_diameter_ox: float | None = None,
    element_diameter_fuel: float | None = None,
    n_elements_ox: int | None = None,
    n_elements_fuel: int | None = None,
) -> InjectorDesign:
    """Design an injector for given operating conditions.

    Sizes orifices for both oxidizer and fuel sides.  The user can
    specify either the number of elements (and the code computes the
    diameter) or the element diameter (and the code computes the count).

    If neither is given, a target element diameter of 1.5 mm is used
    to estimate the element count.

    Args:
        mass_flow: Total propellant mass flow rate [kg/s].
        mixture_ratio: O/F mass ratio.
        chamber_pressure: Chamber pressure [Pa].
        rho_oxidizer: Oxidizer density [kg/m³] (upstream of injector).
        rho_fuel: Fuel density [kg/m³] (upstream of injector).
        dp_fraction: Default pressure-drop fraction of Pc (for both sides).
        dp_fraction_ox: Override pressure-drop fraction for oxidizer.
        dp_fraction_fuel: Override pressure-drop fraction for fuel.
        cd_ox: Oxidizer discharge coefficient.
        cd_fuel: Fuel discharge coefficient.
        element_diameter_ox: Fixed oxidizer orifice diameter [m] (optional).
        element_diameter_fuel: Fixed fuel orifice diameter [m] (optional).
        n_elements_ox: Fixed number of oxidizer elements (optional).
        n_elements_fuel: Fixed number of fuel elements (optional).

    Returns:
        InjectorDesign with complete sizing results.
    """
    # Mass flow split
    mdot_ox = mass_flow * mixture_ratio / (1.0 + mixture_ratio)
    mdot_fuel = mass_flow / (1.0 + mixture_ratio)

    # Pressure drops
    dpf_ox = dp_fraction_ox if dp_fraction_ox is not None else dp_fraction
    dpf_fuel = dp_fraction_fuel if dp_fraction_fuel is not None else dp_fraction
    dp_ox = dpf_ox * chamber_pressure
    dp_fuel = dpf_fuel * chamber_pressure

    # Total required orifice areas
    A_total_ox = orifice_area_from_flow(mdot_ox, cd_ox, dp_ox, rho_oxidizer)
    A_total_fuel = orifice_area_from_flow(mdot_fuel, cd_fuel, dp_fuel, rho_fuel)

    # --- Oxidizer side ---
    if n_elements_ox is not None:
        # Compute element diameter from count
        A_elem_ox = A_total_ox / n_elements_ox
        d_elem_ox = 2.0 * math.sqrt(A_elem_ox / PI)
        n_ox = n_elements_ox
    elif element_diameter_ox is not None:
        # Compute count from element diameter
        A_elem_ox = PI * (element_diameter_ox / 2.0) ** 2
        n_ox = max(1, round(A_total_ox / A_elem_ox))
        d_elem_ox = element_diameter_ox
    else:
        # Default: target 1.5 mm elements
        d_target = 1.5e-3
        A_target = PI * (d_target / 2.0) ** 2
        n_ox = max(1, round(A_total_ox / A_target))
        A_elem_ox = A_total_ox / n_ox
        d_elem_ox = 2.0 * math.sqrt(A_elem_ox / PI)

    v_ox = injection_velocity(cd_ox, dp_ox, rho_oxidizer)

    # --- Fuel side ---
    if n_elements_fuel is not None:
        A_elem_fuel = A_total_fuel / n_elements_fuel
        d_elem_fuel = 2.0 * math.sqrt(A_elem_fuel / PI)
        n_fuel = n_elements_fuel
    elif element_diameter_fuel is not None:
        A_elem_fuel = PI * (element_diameter_fuel / 2.0) ** 2
        n_fuel = max(1, round(A_total_fuel / A_elem_fuel))
        d_elem_fuel = element_diameter_fuel
    else:
        d_target = 1.5e-3
        A_target = PI * (d_target / 2.0) ** 2
        n_fuel = max(1, round(A_total_fuel / A_target))
        A_elem_fuel = A_total_fuel / n_fuel
        d_elem_fuel = 2.0 * math.sqrt(A_elem_fuel / PI)

    v_fuel = injection_velocity(cd_fuel, dp_fuel, rho_fuel)

    # Momentum ratio (important for mixing characterisation)
    mom_ratio = (mdot_ox * v_ox) / (mdot_fuel * v_fuel) if v_fuel > 0 else float("inf")

    return InjectorDesign(
        mass_flow_oxidizer=mdot_ox,
        mass_flow_fuel=mdot_fuel,
        mixture_ratio=mixture_ratio,
        chamber_pressure=chamber_pressure,
        dp_oxidizer=dp_ox,
        dp_fuel=dp_fuel,
        dp_fraction_ox=dpf_ox,
        dp_fraction_fuel=dpf_fuel,
        n_elements_ox=n_ox,
        element_ox=InjectorElement(
            diameter=d_elem_ox,
            area=A_elem_ox,
            cd=cd_ox,
            velocity=v_ox,
        ),
        n_elements_fuel=n_fuel,
        element_fuel=InjectorElement(
            diameter=d_elem_fuel,
            area=A_elem_fuel,
            cd=cd_fuel,
            velocity=v_fuel,
        ),
        manifold_pressure_ox=chamber_pressure + dp_ox,
        manifold_pressure_fuel=chamber_pressure + dp_fuel,
        momentum_ratio=mom_ratio,
    )


def stability_margin(dp: float, chamber_pressure: float) -> float:
    """Injector pressure-drop stability margin.

    A common rule of thumb is ΔP/Pc ≥ 15–20 % for stable combustion.
    Higher ratios provide better feed-coupled stability margins.

    Args:
        dp: Injector pressure drop [Pa].
        chamber_pressure: Chamber pressure [Pa].

    Returns:
        Pressure-drop fraction ΔP/Pc.
    """
    return dp / chamber_pressure


def check_chugging_stability(
    dp_fraction: float,
    min_margin: float = 0.15,
) -> dict[str, float | bool]:
    """Check whether the injector meets the chugging stability criterion.

    Feed-coupled (chugging) instabilities are suppressed when the
    injector pressure drop is a sufficient fraction of chamber pressure.

    Args:
        dp_fraction: ΔP/Pc ratio.
        min_margin: Minimum acceptable ratio (default 15 %).

    Returns:
        Dictionary with stability assessment.
    """
    return {
        "dp_fraction": dp_fraction,
        "min_margin": min_margin,
        "stable": dp_fraction >= min_margin,
        "margin": dp_fraction - min_margin,
    }
