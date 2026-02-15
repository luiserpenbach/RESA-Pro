"""Thermodynamic calculations for rocket engines.

Provides combustion performance estimation, isentropic nozzle flow
relations, and characteristic velocity / thrust coefficient calculations.

Note: This module provides simplified combustion calculations using
pre-tabulated data and ideal/frozen flow assumptions. For high-fidelity
equilibrium chemistry, interface with CEA or Cantera externally.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from resa_pro.utils.constants import G_0, R_UNIVERSAL


# --- Pre-tabulated combustion data for common propellant pairs ---
# These are representative values at stoichiometric-ish mixture ratios.
# Production code should interface with CEA or carry full tables.

@dataclass
class CombustionData:
    """Tabulated combustion product properties at a given mixture ratio."""

    oxidizer: str
    fuel: str
    mixture_ratio: float  # O/F by mass
    chamber_temperature: float  # K
    gamma: float  # ratio of specific heats of products
    molar_mass: float  # kg/mol of combustion products
    c_star: float  # m/s — characteristic velocity


# Representative data (approximate, for initial sizing)
_COMBUSTION_TABLE: list[CombustionData] = [
    CombustionData("n2o", "ethanol", 3.0, 2800, 1.23, 0.0245, 1520),
    CombustionData("n2o", "ethanol", 4.0, 3100, 1.21, 0.0260, 1550),
    CombustionData("n2o", "ethanol", 5.0, 3200, 1.19, 0.0270, 1540),
    CombustionData("lox", "ethanol", 1.5, 3200, 1.20, 0.0230, 1650),
    CombustionData("lox", "ethanol", 2.0, 3400, 1.18, 0.0240, 1700),
    CombustionData("lox", "rp1", 2.3, 3500, 1.22, 0.0230, 1750),
    CombustionData("lox", "rp1", 2.7, 3600, 1.20, 0.0235, 1780),
    CombustionData("lox", "methane", 3.0, 3400, 1.19, 0.0210, 1780),
    CombustionData("lox", "methane", 3.5, 3550, 1.17, 0.0220, 1800),
    CombustionData("lox", "hydrogen", 5.0, 3200, 1.25, 0.0120, 2300),
    CombustionData("lox", "hydrogen", 6.0, 3400, 1.22, 0.0130, 2350),
]


def lookup_combustion(
    oxidizer: str, fuel: str, mixture_ratio: float | None = None
) -> CombustionData:
    """Look up combustion data for a propellant pair.

    If mixture_ratio is given, selects the closest match; otherwise returns
    the entry with the highest c*.

    Args:
        oxidizer: Oxidizer name (e.g. "n2o", "lox").
        fuel: Fuel name (e.g. "ethanol", "rp1").
        mixture_ratio: O/F mass ratio. If None, returns the optimal entry.

    Raises:
        KeyError: If propellant combination is not in the table.
    """
    matches = [
        d
        for d in _COMBUSTION_TABLE
        if d.oxidizer.lower() == oxidizer.lower() and d.fuel.lower() == fuel.lower()
    ]
    if not matches:
        available = {(d.oxidizer, d.fuel) for d in _COMBUSTION_TABLE}
        raise KeyError(
            f"No combustion data for {oxidizer}/{fuel}. Available pairs: {available}"
        )

    if mixture_ratio is not None:
        matches.sort(key=lambda d: abs(d.mixture_ratio - mixture_ratio))
        return matches[0]

    # Return highest c*
    return max(matches, key=lambda d: d.c_star)


# --- Isentropic nozzle flow ---


def area_ratio_from_mach(M: float, gamma: float) -> float:
    """Compute A/A* (area ratio) from Mach number using isentropic relation.

    Args:
        M: Mach number (> 0).
        gamma: Ratio of specific heats.

    Returns:
        Area ratio A/A*.
    """
    g = gamma
    gp1 = g + 1.0
    gm1 = g - 1.0
    exponent = gp1 / (2.0 * gm1)
    return (1.0 / M) * ((2.0 / gp1) * (1.0 + 0.5 * gm1 * M**2)) ** exponent


def mach_from_area_ratio(area_ratio: float, gamma: float, supersonic: bool = True) -> float:
    """Invert the area-Mach relation to find Mach number.

    Args:
        area_ratio: A/A* (must be >= 1).
        gamma: Ratio of specific heats.
        supersonic: If True return the supersonic solution, else subsonic.

    Returns:
        Mach number.
    """
    if area_ratio < 1.0:
        raise ValueError(f"Area ratio must be >= 1.0, got {area_ratio}")

    def residual(M: float) -> float:
        return area_ratio_from_mach(M, gamma) - area_ratio

    if supersonic:
        M = brentq(residual, 1.0, 50.0)
    else:
        M = brentq(residual, 1e-6, 1.0)
    return M


def pressure_ratio(M: float, gamma: float) -> float:
    """Isentropic pressure ratio P/P0 at Mach number M."""
    return (1.0 + 0.5 * (gamma - 1.0) * M**2) ** (-gamma / (gamma - 1.0))


def temperature_ratio(M: float, gamma: float) -> float:
    """Isentropic temperature ratio T/T0 at Mach number M."""
    return (1.0 + 0.5 * (gamma - 1.0) * M**2) ** (-1.0)


def density_ratio(M: float, gamma: float) -> float:
    """Isentropic density ratio rho/rho0 at Mach number M."""
    return (1.0 + 0.5 * (gamma - 1.0) * M**2) ** (-1.0 / (gamma - 1.0))


# --- Performance parameters ---


def characteristic_velocity(gamma: float, R_specific: float, Tc: float) -> float:
    """Characteristic exhaust velocity c* [m/s].

    Args:
        gamma: Ratio of specific heats of combustion products.
        R_specific: Specific gas constant [J/(kg·K)] = R_universal / M.
        Tc: Chamber (stagnation) temperature [K].

    Returns:
        c* in m/s.
    """
    g = gamma
    gp1 = g + 1.0
    gm1 = g - 1.0
    return math.sqrt(R_specific * Tc) / (
        g * math.sqrt((2.0 / gp1) ** (gp1 / gm1))
    )


def thrust_coefficient(gamma: float, expansion_ratio: float, pe_pc: float, pa_pc: float = 0.0) -> float:
    """Thrust coefficient CF.

    Args:
        gamma: Ratio of specific heats.
        expansion_ratio: Nozzle area ratio Ae/At.
        pe_pc: Exit-to-chamber pressure ratio pe/pc.
        pa_pc: Ambient-to-chamber pressure ratio pa/pc (0 for vacuum).

    Returns:
        Thrust coefficient CF.
    """
    g = gamma
    gm1 = g - 1.0
    gp1 = g + 1.0

    # Momentum thrust term
    cf_momentum = math.sqrt(
        (2.0 * g**2 / gm1) * (2.0 / gp1) ** (gp1 / gm1) * (1.0 - pe_pc ** (gm1 / g))
    )
    # Pressure thrust term
    cf_pressure = (pe_pc - pa_pc) * expansion_ratio

    return cf_momentum + cf_pressure


def exit_pressure_ratio(gamma: float, expansion_ratio: float) -> float:
    """Calculate pe/pc from expansion ratio using isentropic relations.

    Args:
        gamma: Ratio of specific heats.
        expansion_ratio: Ae/At.

    Returns:
        pe/pc pressure ratio.
    """
    Me = mach_from_area_ratio(expansion_ratio, gamma, supersonic=True)
    return pressure_ratio(Me, gamma)


def specific_impulse(c_star: float, CF: float) -> float:
    """Specific impulse Isp [s] from c* and CF.

    Isp = c* · CF / g0
    """
    return c_star * CF / G_0


def exhaust_velocity(c_star: float, CF: float) -> float:
    """Effective exhaust velocity ve [m/s]."""
    return c_star * CF


def throat_area(thrust: float, pc: float, CF: float) -> float:
    """Throat area [m²] from thrust [N], chamber pressure [Pa], and CF.

    F = CF · Pc · At  →  At = F / (CF · Pc)
    """
    return thrust / (CF * pc)


def mass_flow_rate(pc: float, At: float, c_star: float) -> float:
    """Total propellant mass flow rate [kg/s].

    ṁ = Pc · At / c*
    """
    return pc * At / c_star


@dataclass
class NozzlePerformance:
    """Collection of nozzle performance parameters."""

    gamma: float
    expansion_ratio: float
    exit_mach: float
    pe_pc: float  # exit pressure / chamber pressure
    CF_vac: float  # vacuum thrust coefficient
    CF_sl: float  # sea-level thrust coefficient
    c_star: float  # m/s
    Isp_vac: float  # s
    Isp_sl: float  # s
    ve_vac: float  # m/s — effective exhaust velocity (vacuum)


def compute_nozzle_performance(
    gamma: float,
    molar_mass: float,
    Tc: float,
    expansion_ratio: float,
    pc: float,
    pa: float = 101325.0,
) -> NozzlePerformance:
    """Compute complete ideal nozzle performance.

    Args:
        gamma: Ratio of specific heats of combustion products.
        molar_mass: Molar mass of combustion products [kg/mol].
        Tc: Chamber temperature [K].
        expansion_ratio: Ae/At.
        pc: Chamber pressure [Pa].
        pa: Ambient pressure [Pa] (default: sea level).

    Returns:
        NozzlePerformance dataclass with all key parameters.
    """
    R_spec = R_UNIVERSAL / molar_mass
    c_s = characteristic_velocity(gamma, R_spec, Tc)
    Me = mach_from_area_ratio(expansion_ratio, gamma, supersonic=True)
    pe_pc = pressure_ratio(Me, gamma)
    pa_pc = pa / pc

    CF_vac = thrust_coefficient(gamma, expansion_ratio, pe_pc, pa_pc=0.0)
    CF_sl = thrust_coefficient(gamma, expansion_ratio, pe_pc, pa_pc=pa_pc)

    return NozzlePerformance(
        gamma=gamma,
        expansion_ratio=expansion_ratio,
        exit_mach=Me,
        pe_pc=pe_pc,
        CF_vac=CF_vac,
        CF_sl=CF_sl,
        c_star=c_s,
        Isp_vac=specific_impulse(c_s, CF_vac),
        Isp_sl=specific_impulse(c_s, CF_sl),
        ve_vac=exhaust_velocity(c_s, CF_vac),
    )
