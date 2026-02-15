"""Chamber sizing module for RESA Pro.

Computes combustion chamber geometry from either direct dimensions or
performance requirements (thrust, chamber pressure, propellant combination).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from resa_pro.core.thermo import (
    compute_nozzle_performance,
    lookup_combustion,
    mass_flow_rate,
    throat_area,
)
from resa_pro.utils.constants import PI


@dataclass
class ChamberGeometry:
    """Complete chamber geometry definition.

    All dimensions in SI (metres) unless noted.
    """

    # Throat
    throat_diameter: float = 0.0  # m
    throat_radius: float = 0.0  # m
    throat_area: float = 0.0  # m²

    # Chamber
    chamber_diameter: float = 0.0  # m
    chamber_radius: float = 0.0  # m
    chamber_area: float = 0.0  # m²
    chamber_length: float = 0.0  # m
    chamber_volume: float = 0.0  # m³
    contraction_ratio: float = 0.0  # Ac/At
    l_star: float = 0.0  # m — characteristic length

    # Convergent section
    convergent_half_angle: float = math.radians(30)  # rad
    convergent_length: float = 0.0  # m
    throat_upstream_radius: float = 0.0  # m — upstream throat rounding radius
    throat_downstream_radius: float = 0.0  # m — downstream throat rounding radius

    # Operating point
    chamber_pressure: float = 0.0  # Pa
    thrust: float = 0.0  # N
    mass_flow: float = 0.0  # kg/s
    mixture_ratio: float = 0.0  # O/F

    # Contour points (x=axial from injector face, y=radius)
    contour_x: np.ndarray = field(default_factory=lambda: np.array([]))
    contour_y: np.ndarray = field(default_factory=lambda: np.array([]))


def size_chamber_from_thrust(
    thrust: float,
    chamber_pressure: float,
    oxidizer: str = "n2o",
    fuel: str = "ethanol",
    mixture_ratio: float | None = None,
    l_star: float = 1.2,
    contraction_ratio: float = 3.0,
    convergent_half_angle: float = 30.0,
    throat_upstream_rc_ratio: float = 1.5,
    throat_downstream_rc_ratio: float = 0.4,
) -> ChamberGeometry:
    """Size a combustion chamber from thrust and chamber pressure.

    Args:
        thrust: Design thrust [N].
        chamber_pressure: Chamber pressure [Pa].
        oxidizer: Oxidizer name for combustion lookup.
        fuel: Fuel name for combustion lookup.
        mixture_ratio: O/F mass ratio. If None, uses optimal from table.
        l_star: Characteristic chamber length [m].
        contraction_ratio: Chamber-to-throat area ratio Ac/At.
        convergent_half_angle: Convergent cone half-angle [degrees].
        throat_upstream_rc_ratio: Upstream throat rounding radius / throat radius.
        throat_downstream_rc_ratio: Downstream throat rounding radius / throat radius.

    Returns:
        ChamberGeometry with all dimensions populated.
    """
    comb = lookup_combustion(oxidizer, fuel, mixture_ratio)

    # Use a nominal expansion ratio of 1 to get c* and CF for sizing
    # We only need c* for mass flow and At
    perf = compute_nozzle_performance(
        gamma=comb.gamma,
        molar_mass=comb.molar_mass,
        Tc=comb.chamber_temperature,
        expansion_ratio=5.0,  # nominal; doesn't affect c*
        pc=chamber_pressure,
    )

    # Throat area: At = F / (CF_vac * Pc)  — using vacuum CF for sizing
    At = throat_area(thrust, chamber_pressure, perf.CF_vac)
    Rt = math.sqrt(At / PI)
    Dt = 2.0 * Rt

    # Chamber dimensions
    Ac = contraction_ratio * At
    Rc = math.sqrt(Ac / PI)
    Dc = 2.0 * Rc

    # Chamber volume from L*: V_c = L* · At
    Vc = l_star * At

    # Chamber cylindrical length (approximate, subtracting convergent volume)
    conv_half_rad = math.radians(convergent_half_angle)
    # Convergent section modeled as truncated cone
    conv_length = (Rc - Rt) / math.tan(conv_half_rad)
    # Volume of convergent truncated cone
    conv_volume = (PI * conv_length / 3.0) * (Rc**2 + Rc * Rt + Rt**2)
    # Cylindrical chamber length
    Lc = max((Vc - conv_volume) / Ac, 0.01)  # minimum 10mm

    # Throat rounding radii
    Ru = throat_upstream_rc_ratio * Rt
    Rd = throat_downstream_rc_ratio * Rt

    # Mass flow
    mdot = mass_flow_rate(chamber_pressure, At, perf.c_star)

    geom = ChamberGeometry(
        throat_diameter=Dt,
        throat_radius=Rt,
        throat_area=At,
        chamber_diameter=Dc,
        chamber_radius=Rc,
        chamber_area=Ac,
        chamber_length=Lc,
        chamber_volume=Vc,
        contraction_ratio=contraction_ratio,
        l_star=l_star,
        convergent_half_angle=conv_half_rad,
        convergent_length=conv_length,
        throat_upstream_radius=Ru,
        throat_downstream_radius=Rd,
        chamber_pressure=chamber_pressure,
        thrust=thrust,
        mass_flow=mdot,
        mixture_ratio=comb.mixture_ratio if mixture_ratio is None else mixture_ratio,
    )

    # Generate contour
    geom.contour_x, geom.contour_y = generate_chamber_contour(geom)
    return geom


def size_chamber_from_dimensions(
    throat_diameter: float,
    chamber_diameter: float | None = None,
    contraction_ratio: float | None = None,
    l_star: float = 1.2,
    convergent_half_angle: float = 30.0,
    throat_upstream_rc_ratio: float = 1.5,
    throat_downstream_rc_ratio: float = 0.4,
) -> ChamberGeometry:
    """Size a chamber from direct geometric inputs.

    Must provide either chamber_diameter or contraction_ratio (not both).

    Args:
        throat_diameter: Throat diameter [m].
        chamber_diameter: Chamber diameter [m] (optional).
        contraction_ratio: Ac/At ratio (optional, used if chamber_diameter not given).
        l_star: Characteristic length [m].
        convergent_half_angle: Convergent half-angle [degrees].

    Returns:
        ChamberGeometry.
    """
    Rt = throat_diameter / 2.0
    At = PI * Rt**2

    if chamber_diameter is not None:
        Rc = chamber_diameter / 2.0
        cr = (Rc / Rt) ** 2
    elif contraction_ratio is not None:
        cr = contraction_ratio
        Rc = Rt * math.sqrt(cr)
    else:
        raise ValueError("Provide either chamber_diameter or contraction_ratio")

    Ac = PI * Rc**2
    Vc = l_star * At

    conv_half_rad = math.radians(convergent_half_angle)
    conv_length = (Rc - Rt) / math.tan(conv_half_rad)
    conv_volume = (PI * conv_length / 3.0) * (Rc**2 + Rc * Rt + Rt**2)
    Lc = max((Vc - conv_volume) / Ac, 0.01)

    Ru = throat_upstream_rc_ratio * Rt
    Rd = throat_downstream_rc_ratio * Rt

    geom = ChamberGeometry(
        throat_diameter=2.0 * Rt,
        throat_radius=Rt,
        throat_area=At,
        chamber_diameter=2.0 * Rc,
        chamber_radius=Rc,
        chamber_area=Ac,
        chamber_length=Lc,
        chamber_volume=Vc,
        contraction_ratio=cr,
        l_star=l_star,
        convergent_half_angle=conv_half_rad,
        convergent_length=conv_length,
        throat_upstream_radius=Ru,
        throat_downstream_radius=Rd,
    )
    geom.contour_x, geom.contour_y = generate_chamber_contour(geom)
    return geom


def generate_chamber_contour(
    geom: ChamberGeometry,
    num_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate the axisymmetric inner wall contour of the chamber.

    Produces points from the injector face through the cylindrical section,
    convergent section (with throat rounding arcs), to the throat plane.

    The contour uses:
    - Straight cylindrical section
    - Tangent-arc convergent entry
    - Conical convergent
    - Upstream circular arc blending into the throat

    Args:
        geom: ChamberGeometry with dimensions set.
        num_points: Total number of contour points.

    Returns:
        (x, y) arrays where x is axial distance from injector face
        and y is the wall radius.
    """
    Rc = geom.chamber_radius
    Rt = geom.throat_radius
    Lc = geom.chamber_length
    Ru = geom.throat_upstream_radius
    beta = geom.convergent_half_angle

    # --- Section 1: Cylindrical chamber ---
    n_cyl = num_points // 3
    x_cyl = np.linspace(0, Lc, n_cyl, endpoint=False)
    y_cyl = np.full_like(x_cyl, Rc)

    # --- Section 2: Convergent cone (from chamber to upstream throat arc tangent point) ---
    # The upstream arc is tangent to the cone at a point above the throat.
    # Tangent point on upstream arc:
    #   y_tang = Rt + Ru * (1 - cos(beta))
    #   The cone runs from Rc down to y_tang.
    y_tang = Rt + Ru * (1.0 - math.cos(beta))
    x_tang = Lc + (Rc - y_tang) / math.tan(beta)  # axial position of tangent point

    n_conv = num_points // 3
    x_conv = np.linspace(Lc, x_tang, n_conv, endpoint=False)
    y_conv = Rc - (x_conv - Lc) * math.tan(beta)

    # --- Section 3: Upstream throat circular arc ---
    # Arc from tangent point to throat (angle sweeps from beta to 0)
    # Arc center: (x_center, Rt + Ru)
    x_center = x_tang + Ru * math.sin(beta)
    y_center = Rt + Ru

    n_arc = num_points - n_cyl - n_conv
    theta = np.linspace(PI / 2 + beta, PI / 2, n_arc)
    x_arc = x_center + Ru * np.cos(theta)
    y_arc = y_center - Ru * np.sin(theta)

    x = np.concatenate([x_cyl, x_conv, x_arc])
    y = np.concatenate([y_cyl, y_conv, y_arc])

    return x, y
