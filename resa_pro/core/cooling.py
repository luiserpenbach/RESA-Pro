"""Regenerative cooling analysis module for RESA Pro.

Provides channel geometry definition, coolant-side heat transfer
correlations, wall temperature estimation, and pressure-drop
calculations for regenerative cooling jackets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from resa_pro.utils.constants import PI


@dataclass
class CoolingChannel:
    """Cooling channel cross-section geometry.

    Rectangular channel geometry is assumed (most common for milled or
    electroformed regenerative jackets).
    """

    width: float = 1.0e-3  # m — channel width
    height: float = 2.0e-3  # m — channel height (radial depth)
    wall_thickness: float = 1.0e-3  # m — inner (hot-gas-side) wall thickness
    fin_width: float = 1.0e-3  # m — land (rib) width between channels
    n_channels: int = 40  # number of channels around circumference

    @property
    def area(self) -> float:
        """Channel cross-sectional flow area [m²]."""
        return self.width * self.height

    @property
    def wetted_perimeter(self) -> float:
        """Wetted perimeter of rectangular channel [m]."""
        return 2.0 * (self.width + self.height)

    @property
    def hydraulic_diameter(self) -> float:
        """Hydraulic diameter Dh = 4A/P [m]."""
        return 4.0 * self.area / self.wetted_perimeter

    @property
    def total_flow_area(self) -> float:
        """Total coolant flow area across all channels [m²]."""
        return self.n_channels * self.area


def size_channels(
    local_radius: float,
    channel_width: float = 1.0e-3,
    fin_width: float = 1.0e-3,
    channel_height: float = 2.0e-3,
    wall_thickness: float = 1.0e-3,
) -> CoolingChannel:
    """Size the number of cooling channels for a given local radius.

    Channels are distributed around the circumference at the specified
    axial station.  The number of channels is computed from the
    available circumference and channel + fin pitch.

    Args:
        local_radius: Inner wall radius at this station [m].
        channel_width: Channel width [m].
        fin_width: Land / fin width between channels [m].
        channel_height: Channel depth (radial) [m].
        wall_thickness: Hot-gas-side wall thickness [m].

    Returns:
        CoolingChannel with dimensions and channel count.
    """
    outer_radius = local_radius + wall_thickness + channel_height
    circumference = 2.0 * PI * (local_radius + wall_thickness + channel_height / 2.0)
    pitch = channel_width + fin_width
    n = max(1, int(circumference / pitch))

    return CoolingChannel(
        width=channel_width,
        height=channel_height,
        wall_thickness=wall_thickness,
        fin_width=fin_width,
        n_channels=n,
    )


def coolant_htc_dittus_boelter(
    Re: float,
    Pr: float,
    k: float,
    Dh: float,
    heating: bool = True,
) -> float:
    """Dittus-Boelter correlation for turbulent forced convection.

    Nu = 0.023 · Re^0.8 · Pr^n
    where n = 0.4 for heating, 0.3 for cooling.

    Args:
        Re: Reynolds number.
        Pr: Prandtl number.
        k: Thermal conductivity of coolant [W/(m·K)].
        Dh: Hydraulic diameter [m].
        heating: True if fluid is being heated (default).

    Returns:
        Coolant-side heat transfer coefficient [W/(m²·K)].
    """
    n = 0.4 if heating else 0.3
    Nu = 0.023 * Re**0.8 * Pr**n
    return Nu * k / Dh


def coolant_htc_sieder_tate(
    Re: float,
    Pr: float,
    k: float,
    Dh: float,
    mu_bulk: float,
    mu_wall: float,
) -> float:
    """Sieder-Tate correlation for turbulent convection with viscosity correction.

    Nu = 0.027 · Re^0.8 · Pr^(1/3) · (μ_bulk / μ_wall)^0.14

    Better than Dittus-Boelter when wall-to-bulk temperature difference
    is large (common in regen cooling).

    Args:
        Re: Reynolds number.
        Pr: Prandtl number.
        k: Thermal conductivity of coolant [W/(m·K)].
        Dh: Hydraulic diameter [m].
        mu_bulk: Bulk dynamic viscosity [Pa·s].
        mu_wall: Wall dynamic viscosity [Pa·s].

    Returns:
        Coolant-side heat transfer coefficient [W/(m²·K)].
    """
    Nu = 0.027 * Re**0.8 * Pr ** (1.0 / 3.0) * (mu_bulk / mu_wall) ** 0.14
    return Nu * k / Dh


def channel_pressure_drop(
    length: float,
    Dh: float,
    rho: float,
    velocity: float,
    Re: float,
    roughness: float = 3.0e-6,
) -> float:
    """Frictional pressure drop in a cooling channel [Pa].

    Uses the Darcy-Weisbach equation with the Colebrook friction factor.

    Args:
        length: Channel length [m].
        Dh: Hydraulic diameter [m].
        rho: Coolant density [kg/m³].
        velocity: Coolant bulk velocity [m/s].
        Re: Reynolds number.
        roughness: Surface roughness [m] (default 3 μm for milled channels).

    Returns:
        Frictional pressure drop [Pa].
    """
    f = _friction_factor(Re, Dh, roughness)
    return f * (length / Dh) * 0.5 * rho * velocity**2


def _friction_factor(Re: float, Dh: float, roughness: float) -> float:
    """Darcy friction factor using Swamee-Jain approximation.

    Explicit approximation of the Colebrook equation.

    Args:
        Re: Reynolds number.
        Dh: Hydraulic diameter [m].
        roughness: Surface roughness [m].

    Returns:
        Darcy friction factor.
    """
    if Re < 2300:
        # Laminar
        return 64.0 / max(Re, 1.0)

    # Swamee-Jain (1976) explicit approximation
    eps_d = roughness / Dh
    log_arg = eps_d / 3.7 + 5.74 / Re**0.9
    f = 0.25 / (math.log10(log_arg)) ** 2
    return f


@dataclass
class CoolingStation:
    """Results at a single axial station along the cooling jacket."""

    x: float  # m — axial position
    radius: float  # m — local wall radius
    channel: CoolingChannel

    # Gas side
    h_g: float = 0.0  # W/(m²·K) — gas-side HTC
    q_dot: float = 0.0  # W/m² — heat flux
    T_aw: float = 0.0  # K — adiabatic wall temperature

    # Coolant side
    h_c: float = 0.0  # W/(m²·K) — coolant-side HTC
    T_coolant: float = 0.0  # K — bulk coolant temperature
    v_coolant: float = 0.0  # m/s — coolant velocity
    Re: float = 0.0  # Reynolds number
    dp: float = 0.0  # Pa — incremental pressure drop

    # Wall
    T_wg: float = 0.0  # K — gas-side wall temperature
    T_wc: float = 0.0  # K — coolant-side wall temperature
    k_wall: float = 0.0  # W/(m·K) — wall thermal conductivity


@dataclass
class CoolingAnalysisResult:
    """Complete regenerative cooling analysis result."""

    stations: list[CoolingStation] = field(default_factory=list)
    total_pressure_drop: float = 0.0  # Pa
    coolant_outlet_temperature: float = 0.0  # K
    max_wall_temperature: float = 0.0  # K — peak gas-side wall temperature
    max_heat_flux: float = 0.0  # W/m²
    total_heat_load: float = 0.0  # W


def analyze_regen_cooling(
    contour_x: np.ndarray,
    contour_y: np.ndarray,
    throat_radius: float,
    pc: float,
    c_star: float,
    Tc: float,
    gamma: float,
    molar_mass: float,
    coolant_mass_flow: float,
    coolant_inlet_temp: float,
    coolant_cp: float,
    coolant_rho: float,
    coolant_mu: float,
    coolant_k: float,
    wall_conductivity: float,
    channel_width: float = 1.0e-3,
    channel_height: float = 2.0e-3,
    wall_thickness: float = 1.0e-3,
    fin_width: float = 1.0e-3,
    counter_flow: bool = True,
) -> CoolingAnalysisResult:
    """Run a 1-D regenerative cooling analysis along the chamber/nozzle wall.

    Marches station-by-station along the contour, computing gas-side
    heat transfer (Bartz), coolant-side heat transfer (Dittus-Boelter),
    wall temperatures (1-D resistance network), and coolant temperature
    rise.

    The analysis assumes constant coolant properties (no two-phase).
    For a more detailed analysis, couple with the fluids module.

    Args:
        contour_x: Axial positions along wall [m].
        contour_y: Wall radii [m].
        throat_radius: Throat radius [m].
        pc: Chamber pressure [Pa].
        c_star: Characteristic velocity [m/s].
        Tc: Chamber temperature [K].
        gamma: Ratio of specific heats.
        molar_mass: Molar mass of products [kg/mol].
        coolant_mass_flow: Total coolant mass flow [kg/s].
        coolant_inlet_temp: Coolant inlet temperature [K].
        coolant_cp: Coolant specific heat [J/(kg·K)].
        coolant_rho: Coolant density [kg/m³].
        coolant_mu: Coolant dynamic viscosity [Pa·s].
        coolant_k: Coolant thermal conductivity [W/(m·K)].
        wall_conductivity: Wall thermal conductivity [W/(m·K)].
        channel_width: Cooling channel width [m].
        channel_height: Cooling channel depth [m].
        wall_thickness: Hot-gas-side wall thickness [m].
        fin_width: Land width between channels [m].
        counter_flow: If True, coolant flows from nozzle exit toward injector.

    Returns:
        CoolingAnalysisResult with station-by-station data.
    """
    from resa_pro.core.thermal import (
        adiabatic_wall_temperature,
        bartz_heat_transfer_coefficient,
        _mach_from_area_ratio_approx,
    )

    At = PI * throat_radius**2
    Dt = 2.0 * throat_radius

    # Station ordering: if counter-flow, march from nozzle exit to injector
    n = len(contour_x)
    if counter_flow:
        indices = list(range(n - 1, -1, -1))
    else:
        indices = list(range(n))

    T_cool = coolant_inlet_temp
    total_dp = 0.0
    total_heat = 0.0
    max_Twg = 0.0
    max_q = 0.0
    stations: list[CoolingStation] = []

    for i, idx in enumerate(indices):
        x = contour_x[idx]
        r = contour_y[idx]
        A = PI * r**2
        ar = max(A / At, 1.0)

        # Gas-side Mach number and adiabatic wall temperature
        M = _mach_from_area_ratio_approx(ar, gamma) if ar > 1.001 else 1.0
        T_aw = adiabatic_wall_temperature(Tc, gamma, M)

        # Gas-side HTC (Bartz)
        h_g = bartz_heat_transfer_coefficient(
            pc=pc, c_star=c_star, Dt=Dt, Tc=Tc, Tw=max(T_cool + 100, 500),
            gamma=gamma, molar_mass=molar_mass, local_area_ratio=ar,
        )

        # Channel geometry at this station
        chan = size_channels(r, channel_width, fin_width, channel_height, wall_thickness)

        # Coolant velocity and Reynolds number
        v_cool = coolant_mass_flow / (coolant_rho * chan.total_flow_area) if chan.total_flow_area > 0 else 0.0
        Dh = chan.hydraulic_diameter
        Re = coolant_rho * v_cool * Dh / coolant_mu if coolant_mu > 0 else 0.0
        Pr = coolant_mu * coolant_cp / coolant_k if coolant_k > 0 else 0.7

        # Coolant-side HTC
        h_c = coolant_htc_dittus_boelter(Re, Pr, coolant_k, Dh)

        # 1-D wall temperature calculation
        R_g = 1.0 / h_g if h_g > 0 else 1e10
        R_w = wall_thickness / wall_conductivity if wall_conductivity > 0 else 1e10
        R_c = 1.0 / h_c if h_c > 0 else 1e10
        R_total = R_g + R_w + R_c

        q_dot = (T_aw - T_cool) / R_total
        T_wg = T_aw - q_dot * R_g
        T_wc = T_cool + q_dot * R_c

        # Incremental pressure drop
        if i > 0:
            prev_idx = indices[i - 1]
            dx = abs(contour_x[idx] - contour_x[prev_idx])
        else:
            dx = 0.0

        dp_station = channel_pressure_drop(dx, Dh, coolant_rho, v_cool, Re) if dx > 0 else 0.0
        total_dp += dp_station

        # Coolant temperature rise: q · dA = ṁ · cp · dT
        perimeter_heated = 2.0 * PI * r
        dA = perimeter_heated * dx if i > 0 else 0.0
        dQ = q_dot * dA
        total_heat += dQ
        if coolant_mass_flow > 0 and coolant_cp > 0:
            T_cool += dQ / (coolant_mass_flow * coolant_cp)

        max_Twg = max(max_Twg, T_wg)
        max_q = max(max_q, q_dot)

        stations.append(CoolingStation(
            x=x, radius=r, channel=chan,
            h_g=h_g, q_dot=q_dot, T_aw=T_aw,
            h_c=h_c, T_coolant=T_cool, v_coolant=v_cool,
            Re=Re, dp=dp_station,
            T_wg=T_wg, T_wc=T_wc, k_wall=wall_conductivity,
        ))

    return CoolingAnalysisResult(
        stations=stations,
        total_pressure_drop=total_dp,
        coolant_outlet_temperature=T_cool,
        max_wall_temperature=max_Twg,
        max_heat_flux=max_q,
        total_heat_load=total_heat,
    )
