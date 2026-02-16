"""Feed system sizing module for RESA Pro.

Provides tank sizing, pressurisation calculations, and feed line
pressure-drop estimation for pressure-fed and blowdown systems.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from resa_pro.utils.constants import PI, R_UNIVERSAL, G_0


# --- Tank sizing ---


@dataclass
class TankDesign:
    """Propellant tank sizing result."""

    propellant: str = ""
    propellant_mass: float = 0.0  # kg
    propellant_volume: float = 0.0  # m³
    ullage_fraction: float = 0.05  # fractional ullage volume
    total_volume: float = 0.0  # m³
    tank_pressure: float = 0.0  # Pa — MEOP
    inner_diameter: float = 0.0  # m
    inner_radius: float = 0.0  # m
    cylinder_length: float = 0.0  # m — cylindrical section length
    wall_thickness: float = 0.0  # m
    tank_mass: float = 0.0  # kg (structural)
    material: str = ""


def size_tank(
    propellant_mass: float,
    propellant_density: float,
    tank_pressure: float,
    inner_diameter: float,
    material_yield_strength: float,
    material_density: float,
    safety_factor: float = 2.0,
    ullage_fraction: float = 0.05,
    propellant_name: str = "",
    material_name: str = "",
) -> TankDesign:
    """Size a cylindrical propellant tank with hemispherical end caps.

    Uses thin-wall pressure vessel theory (hoop stress) for wall thickness.

    Args:
        propellant_mass: Required propellant mass [kg].
        propellant_density: Propellant density [kg/m³].
        tank_pressure: Maximum expected operating pressure (MEOP) [Pa].
        inner_diameter: Tank inner diameter [m].
        material_yield_strength: Tank material yield strength [Pa].
        material_density: Tank material density [kg/m³].
        safety_factor: Structural safety factor (default 2.0).
        ullage_fraction: Fraction of tank volume reserved for ullage gas.
        propellant_name: Propellant name for labelling.
        material_name: Tank material name for labelling.

    Returns:
        TankDesign with dimensions and mass.
    """
    Ri = inner_diameter / 2.0
    V_prop = propellant_mass / propellant_density
    V_total = V_prop / (1.0 - ullage_fraction)

    # Volume of two hemispherical end caps = one full sphere
    V_caps = (4.0 / 3.0) * PI * Ri**3
    V_cylinder = max(V_total - V_caps, 0.0)
    L_cylinder = V_cylinder / (PI * Ri**2) if Ri > 0 else 0.0

    # Wall thickness: thin-wall hoop stress σ = P·r/t → t = P·r·SF/σ_y
    t_wall = (tank_pressure * Ri * safety_factor) / material_yield_strength

    # Structural mass (cylinder + two hemispherical caps)
    Ro = Ri + t_wall
    V_wall_cylinder = PI * (Ro**2 - Ri**2) * L_cylinder
    V_wall_caps = (4.0 / 3.0) * PI * (Ro**3 - Ri**3)
    tank_mass = (V_wall_cylinder + V_wall_caps) * material_density

    return TankDesign(
        propellant=propellant_name,
        propellant_mass=propellant_mass,
        propellant_volume=V_prop,
        ullage_fraction=ullage_fraction,
        total_volume=V_total,
        tank_pressure=tank_pressure,
        inner_diameter=inner_diameter,
        inner_radius=Ri,
        cylinder_length=L_cylinder,
        wall_thickness=t_wall,
        tank_mass=tank_mass,
        material=material_name,
    )


# --- Pressurant sizing ---


@dataclass
class PressurantDesign:
    """Pressurant (gas) system sizing result."""

    gas: str = ""
    pressurant_mass: float = 0.0  # kg
    bottle_volume: float = 0.0  # m³ — pressurant bottle volume
    bottle_pressure_initial: float = 0.0  # Pa
    bottle_pressure_final: float = 0.0  # Pa
    blowdown_ratio: float = 0.0  # initial/final pressure


def size_pressurant_blowdown(
    tank_volume: float,
    tank_pressure: float,
    pressurant_gamma: float = 1.4,
    pressurant_molar_mass: float = 0.028,
    pressurant_temperature: float = 293.0,
    blowdown_ratio: float = 3.0,
    gas_name: str = "nitrogen",
) -> PressurantDesign:
    """Size a blowdown pressurant system.

    In a blowdown system, high-pressure gas stored in the propellant
    tank ullage (or a separate bottle) expands as propellant is consumed.
    The tank pressure decays from P_initial to P_final.

    For an isentropic blowdown:
        V_gas_initial / V_gas_final = (P_final / P_initial)^(1/γ)

    Simplified: the pressurant bottle must hold enough gas at initial
    pressure to fill the total propellant volume at the final pressure.

    Args:
        tank_volume: Total propellant tank volume to be pressurised [m³].
        tank_pressure: Required minimum feed pressure [Pa] (end of burn).
        pressurant_gamma: Ratio of specific heats of pressurant gas.
        pressurant_molar_mass: Molar mass of pressurant [kg/mol].
        pressurant_temperature: Initial gas temperature [K].
        blowdown_ratio: Ratio of initial to final tank pressure.
        gas_name: Pressurant gas name.

    Returns:
        PressurantDesign with bottle sizing.
    """
    P_final = tank_pressure
    P_initial = blowdown_ratio * P_final

    # Ideal gas: PV = nRT
    # Gas that must fill the tank volume at end-of-burn:
    R_gas = R_UNIVERSAL / pressurant_molar_mass
    # Mass of gas needed to fill tank_volume at P_final and T:
    m_gas = P_final * tank_volume / (R_gas * pressurant_temperature)

    # At initial pressure, this gas occupies a smaller volume:
    V_bottle = m_gas * R_gas * pressurant_temperature / P_initial

    return PressurantDesign(
        gas=gas_name,
        pressurant_mass=m_gas,
        bottle_volume=V_bottle,
        bottle_pressure_initial=P_initial,
        bottle_pressure_final=P_final,
        blowdown_ratio=blowdown_ratio,
    )


def size_pressurant_regulated(
    tank_volume: float,
    regulated_pressure: float,
    bottle_pressure: float = 30.0e6,
    min_bottle_pressure: float = 5.0e6,
    pressurant_molar_mass: float = 0.028,
    pressurant_temperature: float = 293.0,
    gas_name: str = "nitrogen",
) -> PressurantDesign:
    """Size a pressure-regulated pressurant system.

    A pressure regulator maintains constant tank pressure. The pressurant
    bottle must hold enough gas to fill the tank volume at the regulated
    pressure while the bottle pressure drops from initial to minimum.

    Args:
        tank_volume: Total propellant volume to be displaced [m³].
        regulated_pressure: Desired constant tank pressure [Pa].
        bottle_pressure: Initial pressurant bottle pressure [Pa].
        min_bottle_pressure: Minimum usable bottle pressure [Pa].
        pressurant_molar_mass: Molar mass [kg/mol].
        pressurant_temperature: Initial temperature [K].
        gas_name: Pressurant gas name.

    Returns:
        PressurantDesign.
    """
    R_gas = R_UNIVERSAL / pressurant_molar_mass

    # Gas needed to fill tank volume at regulated pressure
    m_gas_delivered = regulated_pressure * tank_volume / (R_gas * pressurant_temperature)

    # Usable pressure range in bottle
    usable_dp = bottle_pressure - min_bottle_pressure

    # Bottle volume: enough gas stored so that Δm·R·T = ΔP·V_bottle
    # m_gas_delivered = ΔP · V_bottle / (R · T)
    V_bottle = m_gas_delivered * R_gas * pressurant_temperature / usable_dp

    # Total pressurant mass in bottle at initial pressure
    m_total = bottle_pressure * V_bottle / (R_gas * pressurant_temperature)

    return PressurantDesign(
        gas=gas_name,
        pressurant_mass=m_total,
        bottle_volume=V_bottle,
        bottle_pressure_initial=bottle_pressure,
        bottle_pressure_final=min_bottle_pressure,
        blowdown_ratio=bottle_pressure / min_bottle_pressure,
    )


# --- Feed line pressure drop ---


@dataclass
class FeedLineResult:
    """Pressure drop result for a feed line segment."""

    length: float = 0.0  # m
    inner_diameter: float = 0.0  # m
    velocity: float = 0.0  # m/s
    reynolds: float = 0.0
    friction_dp: float = 0.0  # Pa — friction loss
    minor_dp: float = 0.0  # Pa — minor losses (fittings, bends)
    gravity_dp: float = 0.0  # Pa — static head
    total_dp: float = 0.0  # Pa


def feed_line_pressure_drop(
    mass_flow: float,
    rho: float,
    mu: float,
    line_diameter: float,
    line_length: float,
    height_change: float = 0.0,
    K_minor: float = 5.0,
    roughness: float = 1.5e-6,
) -> FeedLineResult:
    """Compute pressure drop through a feed line.

    Includes friction (Darcy-Weisbach), minor losses (K-factor), and
    hydrostatic head.

    Args:
        mass_flow: Mass flow rate [kg/s].
        rho: Fluid density [kg/m³].
        mu: Dynamic viscosity [Pa·s].
        line_diameter: Inner diameter of feed line [m].
        line_length: Total line length [m].
        height_change: Elevation change (positive = upward) [m].
        K_minor: Sum of minor loss coefficients for fittings, bends, valves.
        roughness: Pipe inner surface roughness [m].

    Returns:
        FeedLineResult with pressure-drop breakdown.
    """
    A = PI * (line_diameter / 2.0) ** 2
    v = mass_flow / (rho * A) if A > 0 else 0.0
    Re = rho * v * line_diameter / mu if mu > 0 else 0.0

    # Friction factor (Swamee-Jain approximation)
    if Re < 2300:
        f = 64.0 / max(Re, 1.0)
    else:
        eps_d = roughness / line_diameter
        log_arg = eps_d / 3.7 + 5.74 / Re**0.9
        f = 0.25 / (math.log10(log_arg)) ** 2

    dp_friction = f * (line_length / line_diameter) * 0.5 * rho * v**2
    dp_minor = K_minor * 0.5 * rho * v**2
    dp_gravity = rho * G_0 * height_change

    return FeedLineResult(
        length=line_length,
        inner_diameter=line_diameter,
        velocity=v,
        reynolds=Re,
        friction_dp=dp_friction,
        minor_dp=dp_minor,
        gravity_dp=dp_gravity,
        total_dp=dp_friction + dp_minor + dp_gravity,
    )


# --- System-level pressure budget ---


@dataclass
class PressureBudget:
    """System-level pressure budget from tank to chamber."""

    chamber_pressure: float = 0.0  # Pa
    injector_dp: float = 0.0  # Pa
    feed_line_dp: float = 0.0  # Pa
    cooling_dp: float = 0.0  # Pa — regen cooling jacket pressure drop
    valve_dp: float = 0.0  # Pa
    required_tank_pressure: float = 0.0  # Pa
    margin: float = 0.0  # Pa — additional margin


def compute_pressure_budget(
    chamber_pressure: float,
    injector_dp: float,
    feed_line_dp: float = 0.0,
    cooling_dp: float = 0.0,
    valve_dp: float = 50000.0,
    margin_fraction: float = 0.10,
) -> PressureBudget:
    """Compute the required tank pressure from a pressure budget.

    The tank must supply enough pressure to overcome all downstream
    losses and still deliver the required chamber pressure.

    P_tank ≥ Pc + ΔP_inj + ΔP_feed + ΔP_cooling + ΔP_valve + margin

    Args:
        chamber_pressure: Design chamber pressure [Pa].
        injector_dp: Injector pressure drop [Pa].
        feed_line_dp: Feed line pressure losses [Pa].
        cooling_dp: Regen cooling jacket pressure drop [Pa].
        valve_dp: Valve pressure drops [Pa] (default 0.5 bar).
        margin_fraction: Additional margin as fraction of total.

    Returns:
        PressureBudget with required tank pressure.
    """
    subtotal = chamber_pressure + injector_dp + feed_line_dp + cooling_dp + valve_dp
    margin = margin_fraction * subtotal
    required = subtotal + margin

    return PressureBudget(
        chamber_pressure=chamber_pressure,
        injector_dp=injector_dp,
        feed_line_dp=feed_line_dp,
        cooling_dp=cooling_dp,
        valve_dp=valve_dp,
        required_tank_pressure=required,
        margin=margin,
    )
