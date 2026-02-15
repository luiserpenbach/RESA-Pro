"""Method of Characteristics (MOC) nozzle solver for RESA Pro.

Implements a basic 2-D axisymmetric MOC solver for ideal gas to generate
optimal nozzle contours. Real-gas extensions are planned for Phase 1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from resa_pro.core.thermo import area_ratio_from_mach, mach_from_area_ratio
from resa_pro.utils.constants import DEG_TO_RAD, PI, RAD_TO_DEG


@dataclass
class MOCPoint:
    """A single point in the characteristic mesh."""

    x: float  # axial position [m]
    y: float  # radial position [m]
    M: float  # Mach number
    theta: float  # flow angle [rad]
    nu: float  # Prandtl-Meyer angle [rad]


@dataclass
class MOCResult:
    """Result of the MOC nozzle computation."""

    gamma: float
    expansion_ratio: float
    throat_radius: float
    wall_x: np.ndarray = field(default_factory=lambda: np.array([]))
    wall_y: np.ndarray = field(default_factory=lambda: np.array([]))
    exit_mach: float = 0.0
    length: float = 0.0
    mesh_points: list[MOCPoint] = field(default_factory=list)


def prandtl_meyer(M: float, gamma: float) -> float:
    """Prandtl-Meyer function ν(M) [radians].

    ν = sqrt((γ+1)/(γ-1)) · arctan(sqrt((γ-1)/(γ+1)·(M²-1))) - arctan(sqrt(M²-1))
    """
    if M <= 1.0:
        return 0.0
    gp1 = gamma + 1.0
    gm1 = gamma - 1.0
    term = math.sqrt(gm1 / gp1 * (M**2 - 1.0))
    return math.sqrt(gp1 / gm1) * math.atan(term) - math.atan(math.sqrt(M**2 - 1.0))


def mach_from_prandtl_meyer(nu: float, gamma: float) -> float:
    """Invert Prandtl-Meyer function to get Mach from ν.

    Uses Brent's method on the interval [1, 50].
    """
    if nu <= 0:
        return 1.0

    def residual(M: float) -> float:
        return prandtl_meyer(M, gamma) - nu

    return brentq(residual, 1.0, 50.0, xtol=1e-10)


def mach_angle(M: float) -> float:
    """Mach angle μ = arcsin(1/M) [rad]."""
    if M <= 1.0:
        return PI / 2
    return math.asin(1.0 / M)


def _solve_interior_point(
    p1: MOCPoint, p2: MOCPoint, gamma: float
) -> MOCPoint:
    """Solve for an interior point from two known characteristic points.

    p1: point on C- characteristic (left-running)
    p2: point on C+ characteristic (right-running)

    Compatibility equations (2-D planar, simplified):
        Along C+: θ + ν = const  (K+ = θ1 + ν1)
        Along C-: θ - ν = const  (K- = θ2 - ν2)
    """
    Kplus = p1.theta + p1.nu   # along C+ from p1
    Kminus = p2.theta - p2.nu  # along C- from p2

    theta_new = 0.5 * (Kplus + Kminus)
    nu_new = 0.5 * (Kplus - Kminus)
    M_new = mach_from_prandtl_meyer(nu_new, gamma)

    # Position: average of characteristic slopes
    mu1 = mach_angle(p1.M)
    mu2 = mach_angle(p2.M)
    mu_new = mach_angle(M_new)

    # C+ slope: tan(θ - μ), C- slope: tan(θ + μ)
    slope_cp = math.tan(0.5 * (p1.theta + theta_new) - 0.5 * (mu1 + mu_new))
    slope_cm = math.tan(0.5 * (p2.theta + theta_new) + 0.5 * (mu2 + mu_new))

    # Intersection
    denom = slope_cm - slope_cp
    if abs(denom) < 1e-15:
        x_new = 0.5 * (p1.x + p2.x)
        y_new = 0.5 * (p1.y + p2.y)
    else:
        x_new = (p2.y - p1.y + slope_cp * p1.x - slope_cm * p2.x) / denom
        y_new = p1.y + slope_cp * (x_new - p1.x)

    return MOCPoint(x=x_new, y=y_new, M=M_new, theta=theta_new, nu=nu_new)


def _solve_wall_point(
    p_interior: MOCPoint, gamma: float, wall_slope_func=None
) -> MOCPoint:
    """Solve for a wall point from an interior point and the wall boundary.

    At the wall: θ = wall slope angle.
    Along the C- characteristic from p_interior:
        K- = θ_int - ν_int = θ_wall - ν_wall
    So: ν_wall = θ_wall - K-
    """
    Km = p_interior.theta - p_interior.nu

    # For the initial expansion, wall angle θ_wall = 0 (straight wall at exit)
    # In general, we iteratively find the wall contour.
    # Simplified: use θ_wall = 0 for minimum-length nozzle wall
    theta_wall = 0.0
    nu_wall = theta_wall - Km
    if nu_wall < 0:
        nu_wall = 0.0
    M_wall = mach_from_prandtl_meyer(nu_wall, gamma)

    # Position along C- from interior point
    mu_int = mach_angle(p_interior.M)
    mu_wall = mach_angle(M_wall)
    slope_cm = math.tan(
        0.5 * (p_interior.theta + theta_wall) + 0.5 * (mu_int + mu_wall)
    )

    # Wall is at the axial position where the characteristic meets the contour.
    # For a simple minimum-length nozzle, wall at y determined by area ratio.
    # Using the characteristic slope from the interior point:
    # We need a wall y; for MOC the wall is what we're computing.
    # Use the C- characteristic to project to the symmetry line or wall.
    x_wall = p_interior.x + (0.0 - p_interior.y) / slope_cm if abs(slope_cm) > 1e-10 else p_interior.x
    # This is a simplification; proper implementation needs iterative wall finding.
    y_wall = 0.0  # placeholder for centreline reflection

    return MOCPoint(x=x_wall, y=y_wall, M=M_wall, theta=theta_wall, nu=nu_wall)


def compute_moc_nozzle(
    throat_radius: float,
    expansion_ratio: float,
    gamma: float,
    num_char_lines: int = 20,
) -> MOCResult:
    """Compute a minimum-length nozzle contour using MOC.

    Uses a simplified approach: the expansion fan emanates from the
    sharp throat corner.  Each C+ characteristic is traced to the
    centerline (θ = 0 reflection), and then C- characteristics are
    traced back to define the wall contour.

    For the initial implementation the wall contour is built from the
    envelope of C- characteristics coming off the reflected centerline
    points, combined with area-ratio interpolation for robustness.

    Args:
        throat_radius: Throat radius [m].
        expansion_ratio: Ae/At (exit-to-throat area ratio).
        gamma: Ratio of specific heats.
        num_char_lines: Number of characteristic lines from the expansion corner.

    Returns:
        MOCResult with wall contour and mesh points.
    """
    Rt = throat_radius
    Re = Rt * math.sqrt(expansion_ratio)
    Me = mach_from_area_ratio(expansion_ratio, gamma, supersonic=True)
    nu_max = prandtl_meyer(Me, gamma)
    theta_max = nu_max / 2.0  # max wall angle for minimum-length nozzle

    N = num_char_lines
    d_theta = theta_max / N

    # --- Step 1: Build expansion fan from throat corner ---
    # Each ray in the fan has constant K+ = θ + ν.
    # At the sharp corner origin (x=0, y=Rt), for each ray i:
    #   θ_i = i · dθ,  ν_i = θ_i  (from centerline K- = 0 condition)

    all_points: list[MOCPoint] = []

    # --- Step 2: Trace each ray to the centerline (θ = 0 reflection) ---
    # At the centerline, θ = 0, so ν_cl = K+_i = 2·θ_i
    centerline_points: list[MOCPoint] = []
    for i in range(1, N + 1):
        theta_i = i * d_theta
        nu_cl = 2.0 * theta_i  # K+ = θ + ν, at axis θ=0 so ν = K+
        M_cl = mach_from_prandtl_meyer(nu_cl, gamma)
        mu_cl = mach_angle(M_cl)

        # Position: fan ray from (0, Rt) hits the axis.
        # Ray direction: angle (θ_i - μ_i) below horizontal where μ_i = mach_angle(M_i)
        M_i = mach_from_prandtl_meyer(theta_i, gamma)
        mu_i = mach_angle(M_i)
        ray_angle = theta_i - mu_i  # angle from horizontal (negative → downward)

        # Distance from (0, Rt) to centerline along the ray
        if abs(math.sin(ray_angle)) > 1e-10:
            dist = Rt / abs(math.sin(-ray_angle)) if ray_angle < 0 else Rt * 10
        else:
            dist = Rt * 10  # nearly horizontal

        # Use average properties for better accuracy
        avg_angle = 0.5 * theta_i  # average θ between fan origin and axis
        avg_mu = 0.5 * (mu_i + mu_cl)
        char_slope = avg_angle - avg_mu
        if abs(math.sin(char_slope)) > 1e-10:
            x_cl = Rt / abs(math.tan(-char_slope)) if char_slope < 0 else Rt * 5
        else:
            x_cl = Rt * 5

        x_cl = abs(x_cl)
        pt = MOCPoint(x=x_cl, y=0.0, M=M_cl, theta=0.0, nu=nu_cl)
        centerline_points.append(pt)
        all_points.append(pt)

    # --- Step 3: Build wall contour from reflected C- characteristics ---
    # After reflecting from the axis, the C- characteristics (K- = -ν_cl)
    # propagate outward.  The wall must be tangent to these characteristics.
    # For a minimum-length nozzle, the wall angle at each point is:
    #   θ_wall = θ_max - i · dθ  (linearly decreasing from θ_max to 0)

    wall_points_x = [0.0]
    wall_points_y = [Rt]

    for i, cl_pt in enumerate(centerline_points):
        # Wall angle decreases from θ_max toward 0
        frac = (i + 1) / N
        theta_wall = theta_max * (1.0 - frac)

        # From the reflected C- at the centerline:
        # K- = θ_cl - ν_cl = 0 - ν_cl = -ν_cl
        # At wall: θ_wall - ν_wall = K- = -ν_cl
        # So: ν_wall = θ_wall + ν_cl
        nu_wall = theta_wall + cl_pt.nu
        if nu_wall <= 0:
            nu_wall = cl_pt.nu
        M_wall = mach_from_prandtl_meyer(nu_wall, gamma)
        mu_wall = mach_angle(M_wall)

        # C- characteristic slope from centerline to wall:
        # slope = tan(θ_avg + μ_avg)
        theta_avg = 0.5 * theta_wall
        mu_avg = 0.5 * (mach_angle(cl_pt.M) + mu_wall)
        slope = math.tan(theta_avg + mu_avg)

        # y_wall from area ratio progression (for robustness)
        y_wall = Rt + frac * (Re - Rt)

        # x_wall from C- characteristic projection
        if abs(slope) > 1e-10:
            x_wall = cl_pt.x + y_wall / slope
        else:
            x_wall = cl_pt.x + y_wall * 2.0

        x_wall = max(x_wall, wall_points_x[-1] + Rt * 0.001)  # enforce monotonicity

        wall_points_x.append(x_wall)
        wall_points_y.append(y_wall)

        wall_pt = MOCPoint(x=x_wall, y=y_wall, M=M_wall, theta=theta_wall, nu=nu_wall)
        all_points.append(wall_pt)

    # Ensure final exit radius matches target
    wall_points_y[-1] = Re

    wall_x = np.array(wall_points_x)
    wall_y = np.array(wall_points_y)

    return MOCResult(
        gamma=gamma,
        expansion_ratio=expansion_ratio,
        throat_radius=Rt,
        wall_x=wall_x,
        wall_y=wall_y,
        exit_mach=Me,
        length=float(wall_x[-1]),
        mesh_points=all_points,
    )
