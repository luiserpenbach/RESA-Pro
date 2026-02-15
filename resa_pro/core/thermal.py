"""Thermal analysis module for RESA Pro.

Implements Bartz heat transfer correlation, radiative cooling equilibrium,
film cooling effectiveness, and wall temperature estimation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from resa_pro.utils.constants import STEFAN_BOLTZMANN


# --- Bartz equation ---


def bartz_heat_transfer_coefficient(
    pc: float,
    c_star: float,
    Dt: float,
    Tc: float,
    Tw: float,
    gamma: float,
    molar_mass: float,
    local_area_ratio: float,
    Pr: float = 0.5,
    mu_ref: float | None = None,
    cp_ref: float | None = None,
    sigma_correction: bool = True,
) -> float:
    """Bartz convective heat transfer coefficient for hot-gas side.

    The Bartz equation (simplified form):

        h_g = (0.026 / Dt^0.2) · (mu^0.2 · cp / Pr^0.6) · (pc / c*)^0.8
              · (Dt / R_c)^0.1 · (At / A)^0.9 · sigma

    where sigma is a correction factor for property variation across the
    boundary layer.

    Args:
        pc: Chamber pressure [Pa].
        c_star: Characteristic velocity [m/s].
        Dt: Throat diameter [m].
        Tc: Chamber (stagnation) temperature [K].
        Tw: Local wall temperature [K] (hot-gas side).
        gamma: Ratio of specific heats.
        molar_mass: Molar mass of combustion products [kg/mol].
        local_area_ratio: A/At at the location of interest.
        Pr: Prandtl number of combustion gases (~0.5 for most propellants).
        mu_ref: Reference dynamic viscosity [Pa·s]. If None, estimated.
        cp_ref: Reference specific heat [J/(kg·K)]. If None, estimated.
        sigma_correction: Apply Bartz sigma correction for BL temperature.

    Returns:
        Hot-gas side heat transfer coefficient h_g [W/(m²·K)].
    """
    from resa_pro.utils.constants import R_UNIVERSAL

    R_spec = R_UNIVERSAL / molar_mass

    # Estimate transport properties if not provided
    if mu_ref is None:
        # Approximate viscosity using Sutherland-like scaling:
        # mu ~ 1.184e-7 · M^0.5 · T^0.6  (engineering approximation)
        T_ref = 0.5 * (Tc + Tw)
        mu_ref = 1.184e-7 * (molar_mass * 1000) ** 0.5 * T_ref**0.6
    if cp_ref is None:
        cp_ref = gamma * R_spec / (gamma - 1.0)

    # Sigma correction (property variation across boundary layer)
    if sigma_correction:
        T_ratio = 0.5 * (Tw / Tc) + 0.5
        gm1_half = 0.5 * (gamma - 1.0)
        M_local = _mach_from_area_ratio_approx(local_area_ratio, gamma)
        sigma = (
            (T_ratio * (1.0 + gm1_half * M_local**2)) ** 0.68
            * (1.0 + gm1_half * M_local**2) ** 0.12
        ) ** (-1)
    else:
        sigma = 1.0

    h_g = (
        0.026
        / Dt**0.2
        * (mu_ref**0.2 * cp_ref / Pr**0.6)
        * (pc / c_star) ** 0.8
        * (1.0 / local_area_ratio) ** 0.9
        * sigma
    )

    return h_g


def _mach_from_area_ratio_approx(area_ratio: float, gamma: float) -> float:
    """Quick Mach number estimate from area ratio (Newton iteration).

    Used internally for the Bartz sigma correction.
    """
    if area_ratio <= 1.0:
        return 1.0
    # Start with an initial guess
    M = 1.0 + 0.5 * (area_ratio - 1.0)
    for _ in range(20):
        gp1 = gamma + 1.0
        gm1 = gamma - 1.0
        factor = (2.0 / gp1) * (1.0 + 0.5 * gm1 * M**2)
        exp = gp1 / (2.0 * gm1)
        f = (1.0 / M) * factor**exp - area_ratio
        # Derivative (numerical)
        dM = M * 1e-6
        M2 = M + dM
        factor2 = (2.0 / gp1) * (1.0 + 0.5 * gm1 * M2**2)
        f2 = (1.0 / M2) * factor2**exp - area_ratio
        df = (f2 - f) / dM
        if abs(df) < 1e-30:
            break
        M = M - f / df
        M = max(M, 1.001)
        if abs(f) < 1e-10:
            break
    return M


# --- Heat flux calculations ---


@dataclass
class HeatFluxResult:
    """Result of a local heat flux calculation."""

    x: float  # axial position [m]
    area_ratio: float
    h_g: float  # W/(m²·K) — gas-side HTC
    q_dot: float  # W/m² — heat flux
    T_aw: float  # K — adiabatic wall temperature
    T_wg: float  # K — gas-side wall temperature (input)


def adiabatic_wall_temperature(
    Tc: float,
    gamma: float,
    M: float,
    recovery_factor: float = 0.9,
) -> float:
    """Adiabatic (recovery) wall temperature.

    T_aw = Tc · r_f · [1 + (γ-1)/2 · M²] / [1 + (γ-1)/2 · M²]

    Simplified: T_aw = T_static + r_f · (T0 - T_static)

    Args:
        Tc: Chamber stagnation temperature [K].
        gamma: Ratio of specific heats.
        M: Local Mach number.
        recovery_factor: ~Pr^(1/3) for turbulent BL, typically 0.85–0.92.

    Returns:
        Adiabatic wall temperature [K].
    """
    gm1_half = 0.5 * (gamma - 1.0)
    T_static = Tc / (1.0 + gm1_half * M**2)
    T_aw = T_static + recovery_factor * (Tc - T_static)
    return T_aw


def heat_flux(h_g: float, T_aw: float, T_wall: float) -> float:
    """Convective heat flux [W/m²].

    q = h_g · (T_aw - T_wall)
    """
    return h_g * (T_aw - T_wall)


def compute_heat_flux_distribution(
    contour_x: np.ndarray,
    contour_y: np.ndarray,
    throat_radius: float,
    pc: float,
    c_star: float,
    Tc: float,
    gamma: float,
    molar_mass: float,
    T_wall: float = 600.0,
) -> list[HeatFluxResult]:
    """Compute heat flux along the chamber/nozzle wall.

    Args:
        contour_x: Axial positions [m].
        contour_y: Wall radii [m].
        throat_radius: Throat radius [m].
        pc: Chamber pressure [Pa].
        c_star: Characteristic velocity [m/s].
        Tc: Chamber temperature [K].
        gamma: Ratio of specific heats.
        molar_mass: Molar mass of products [kg/mol].
        T_wall: Assumed gas-side wall temperature [K].

    Returns:
        List of HeatFluxResult for each station.
    """
    Dt = 2.0 * throat_radius
    At = math.pi * throat_radius**2
    results = []

    for x, r in zip(contour_x, contour_y):
        A = math.pi * r**2
        ar = A / At
        if ar < 1.0:
            ar = 1.0  # clamp at throat

        M = _mach_from_area_ratio_approx(ar, gamma) if ar > 1.001 else 1.0
        T_aw = adiabatic_wall_temperature(Tc, gamma, M)

        h_g = bartz_heat_transfer_coefficient(
            pc=pc,
            c_star=c_star,
            Dt=Dt,
            Tc=Tc,
            Tw=T_wall,
            gamma=gamma,
            molar_mass=molar_mass,
            local_area_ratio=ar,
        )

        q = heat_flux(h_g, T_aw, T_wall)

        results.append(
            HeatFluxResult(x=x, area_ratio=ar, h_g=h_g, q_dot=q, T_aw=T_aw, T_wg=T_wall)
        )

    return results


# --- Radiative cooling ---


def radiative_equilibrium_temperature(
    q_incident: float,
    emissivity: float = 0.8,
) -> float:
    """Equilibrium wall temperature for a radiation-cooled surface.

    q_incident = ε · σ · T_wall^4  →  T_wall = (q / (ε·σ))^(1/4)

    Args:
        q_incident: Incident heat flux [W/m²].
        emissivity: Surface emissivity (0–1).

    Returns:
        Equilibrium wall temperature [K].
    """
    return (q_incident / (emissivity * STEFAN_BOLTZMANN)) ** 0.25


def radiative_heat_rejection(T_wall: float, emissivity: float = 0.8) -> float:
    """Radiative heat rejection rate per unit area [W/m²].

    q_rad = ε · σ · T^4
    """
    return emissivity * STEFAN_BOLTZMANN * T_wall**4


# --- Simple wall temperature estimation ---


def wall_temperature_simple(
    h_g: float,
    T_aw: float,
    h_c: float,
    T_coolant: float,
    wall_thickness: float,
    wall_conductivity: float,
) -> tuple[float, float]:
    """Estimate gas-side and coolant-side wall temperatures.

    Uses a simple 1-D thermal resistance network:

        T_aw --[1/h_g]-- T_wg --[t_w/k_w]-- T_wc --[1/h_c]-- T_coolant

    Args:
        h_g: Gas-side heat transfer coefficient [W/(m²·K)].
        T_aw: Adiabatic wall temperature [K].
        h_c: Coolant-side heat transfer coefficient [W/(m²·K)].
        T_coolant: Bulk coolant temperature [K].
        wall_thickness: Wall thickness [m].
        wall_conductivity: Wall thermal conductivity [W/(m·K)].

    Returns:
        (T_wg, T_wc) — gas-side and coolant-side wall temperatures [K].
    """
    R_g = 1.0 / h_g
    R_w = wall_thickness / wall_conductivity
    R_c = 1.0 / h_c
    R_total = R_g + R_w + R_c

    q = (T_aw - T_coolant) / R_total
    T_wg = T_aw - q * R_g
    T_wc = T_coolant + q * R_c

    return T_wg, T_wc
