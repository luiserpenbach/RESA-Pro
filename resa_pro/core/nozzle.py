"""Nozzle contour generation and efficiency analysis for RESA Pro.

Supports conical, parabolic (Rao / thrust-optimised), and provides hooks
for the Method of Characteristics solver (see moc.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from resa_pro.utils.constants import DEG_TO_RAD, PI, RAD_TO_DEG


class NozzleMethod(Enum):
    CONICAL = "conical"
    PARABOLIC = "parabolic"  # Rao / thrust-optimised parabola


@dataclass
class NozzleContour:
    """Nozzle contour result."""

    method: NozzleMethod
    expansion_ratio: float
    throat_radius: float  # m

    # Contour points (x = axial from throat, y = radius)
    x: np.ndarray = field(default_factory=lambda: np.array([]))
    y: np.ndarray = field(default_factory=lambda: np.array([]))

    # Key dimensions
    exit_radius: float = 0.0
    length: float = 0.0  # axial length from throat to exit

    # Angles
    half_angle: float = 0.0  # rad — conical half-angle
    theta_initial: float = 0.0  # rad — parabolic initial angle
    theta_exit: float = 0.0  # rad — parabolic exit angle

    # Divergence efficiency
    divergence_efficiency: float = 1.0


# --- Conical nozzle ---


def conical_nozzle(
    throat_radius: float,
    expansion_ratio: float,
    half_angle: float = 15.0,
    downstream_rc_ratio: float = 0.4,
    num_points: int = 200,
) -> NozzleContour:
    """Generate a conical nozzle contour.

    The contour includes a downstream circular arc transitioning from the
    throat into the straight conical divergent section.

    Args:
        throat_radius: Throat radius [m].
        expansion_ratio: Ae/At.
        half_angle: Cone half-angle [degrees].
        downstream_rc_ratio: Downstream throat rounding radius / Rt.
        num_points: Number of contour points.

    Returns:
        NozzleContour with points starting at the throat.
    """
    Rt = throat_radius
    Re = Rt * math.sqrt(expansion_ratio)
    alpha = half_angle * DEG_TO_RAD
    Rd = downstream_rc_ratio * Rt  # downstream rounding radius

    # Downstream arc: from throat (angle 0) to cone tangent point (angle alpha)
    # Arc center at (0, Rt + Rd)
    y_center = Rt + Rd
    n_arc = num_points // 4
    theta_arc = np.linspace(PI / 2, PI / 2 - alpha, n_arc, endpoint=False)
    x_arc = Rd * np.cos(theta_arc)  # starts at 0
    y_arc = y_center - Rd * np.sin(theta_arc)

    # Tangent point on arc
    x_t = Rd * math.sin(alpha)
    y_t = Rt + Rd * (1.0 - math.cos(alpha))

    # Straight cone from tangent point to exit
    cone_length = (Re - y_t) / math.tan(alpha)
    n_cone = num_points - n_arc
    x_cone = np.linspace(x_t, x_t + cone_length, n_cone)
    y_cone = y_t + (x_cone - x_t) * math.tan(alpha)

    x = np.concatenate([x_arc, x_cone])
    y = np.concatenate([y_arc, y_cone])

    # Divergence efficiency for conical nozzle: lambda = (1 + cos(alpha)) / 2
    div_eff = (1.0 + math.cos(alpha)) / 2.0

    return NozzleContour(
        method=NozzleMethod.CONICAL,
        expansion_ratio=expansion_ratio,
        throat_radius=Rt,
        x=x,
        y=y,
        exit_radius=Re,
        length=x[-1],
        half_angle=alpha,
        divergence_efficiency=div_eff,
    )


# --- Parabolic (Rao / thrust-optimised) nozzle ---

# Empirical Rao nozzle angles as a function of expansion ratio and fractional
# length Lf (% of equivalent 15° conical length).
# Source: Rao, 1958 & Huzel/Huang "Modern Engineering for Design of
# Liquid-Propellant Rocket Engines".
#
# These are approximate curve-fit correlations.


def _rao_angles(expansion_ratio: float, Lf: float = 0.8) -> tuple[float, float]:
    """Estimate initial and exit wall angles for a Rao parabolic nozzle.

    Args:
        expansion_ratio: Ae/At.
        Lf: Fractional length relative to 15° conical (typically 0.6–0.9).

    Returns:
        (theta_initial, theta_exit) in radians.
    """
    eps = expansion_ratio

    # Empirical fits (valid roughly for eps 4–60, Lf 0.6–0.9)
    # theta_initial ≈ function primarily of Lf
    theta_i_deg = 21.0 + 14.0 * (1.0 - Lf)  # ~21° at Lf=0.8, ~35° at Lf=0.6
    # theta_exit decreases with expansion ratio
    theta_e_deg = max(7.0 - 0.15 * (eps - 10.0), 3.0)  # clamp minimum 3°
    if Lf < 0.7:
        theta_e_deg += 2.0
    elif Lf > 0.85:
        theta_e_deg -= 1.5

    return theta_i_deg * DEG_TO_RAD, max(theta_e_deg, 2.0) * DEG_TO_RAD


def parabolic_nozzle(
    throat_radius: float,
    expansion_ratio: float,
    fractional_length: float = 0.8,
    theta_initial: float | None = None,
    theta_exit: float | None = None,
    downstream_rc_ratio: float = 0.4,
    num_points: int = 200,
) -> NozzleContour:
    """Generate a parabolic (Rao-type) nozzle contour.

    Uses a quadratic Bezier curve between the downstream throat arc tangent
    point and the nozzle exit plane, constrained by the initial and exit
    wall angles.

    Args:
        throat_radius: Throat radius [m].
        expansion_ratio: Ae/At.
        fractional_length: Fraction of equivalent 15° cone length (0.6–0.9).
        theta_initial: Initial wall angle [degrees]. If None, estimated.
        theta_exit: Exit wall angle [degrees]. If None, estimated.
        downstream_rc_ratio: Downstream throat arc radius / Rt.
        num_points: Number of contour points.

    Returns:
        NozzleContour.
    """
    Rt = throat_radius
    Re = Rt * math.sqrt(expansion_ratio)
    Rd = downstream_rc_ratio * Rt

    # Get angles
    if theta_initial is None or theta_exit is None:
        ti_est, te_est = _rao_angles(expansion_ratio, fractional_length)
        if theta_initial is None:
            theta_initial = ti_est
        else:
            theta_initial = theta_initial * DEG_TO_RAD
        if theta_exit is None:
            theta_exit = te_est
        else:
            theta_exit = theta_exit * DEG_TO_RAD
    else:
        theta_initial = theta_initial * DEG_TO_RAD
        theta_exit = theta_exit * DEG_TO_RAD

    # --- Downstream circular arc (throat to tangent point) ---
    y_center = Rt + Rd
    n_arc = num_points // 4
    theta_arc = np.linspace(PI / 2, PI / 2 - theta_initial, n_arc, endpoint=True)
    x_arc = Rd * np.cos(theta_arc)
    y_arc = y_center - Rd * np.sin(theta_arc)

    # Start point of parabola = end of arc
    xN = x_arc[-1]
    yN = y_arc[-1]

    # End point of parabola
    # Length of equivalent 15° cone
    L_15 = (Re - Rt) / math.tan(15.0 * DEG_TO_RAD)
    L_nozzle = fractional_length * L_15
    xE = L_nozzle
    yE = Re

    # Quadratic Bezier: P(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
    # P0 = (xN, yN), P2 = (xE, yE)
    # Tangent at P0 has slope tan(theta_initial)
    # Tangent at P2 has slope tan(theta_exit)
    # Intersection of tangent lines gives P1
    m0 = math.tan(theta_initial)
    m1 = math.tan(theta_exit)

    if abs(m0 - m1) < 1e-12:
        # Degenerate: straight line
        xP1 = (xN + xE) / 2
        yP1 = (yN + yE) / 2
    else:
        xP1 = (yE - yN + m0 * xN - m1 * xE) / (m0 - m1)
        yP1 = yN + m0 * (xP1 - xN)

    n_para = num_points - n_arc
    t = np.linspace(0, 1, n_para)
    x_para = (1 - t) ** 2 * xN + 2 * (1 - t) * t * xP1 + t**2 * xE
    y_para = (1 - t) ** 2 * yN + 2 * (1 - t) * t * yP1 + t**2 * yE

    x = np.concatenate([x_arc[:-1], x_para])  # avoid duplicate at junction
    y = np.concatenate([y_arc[:-1], y_para])

    # Divergence efficiency for parabolic nozzle (approximation)
    # Generally > conical; use average angle approach
    avg_angle = (theta_initial + theta_exit) / 2.0
    div_eff = (1.0 + math.cos(avg_angle)) / 2.0

    return NozzleContour(
        method=NozzleMethod.PARABOLIC,
        expansion_ratio=expansion_ratio,
        throat_radius=Rt,
        x=x,
        y=y,
        exit_radius=Re,
        length=x[-1],
        theta_initial=theta_initial,
        theta_exit=theta_exit,
        divergence_efficiency=div_eff,
    )


# --- Efficiency analysis ---


@dataclass
class NozzleEfficiency:
    """Breakdown of nozzle efficiency losses."""

    divergence_efficiency: float = 1.0
    boundary_layer_loss: float = 0.0  # fractional loss
    two_phase_loss: float = 0.0
    total_efficiency: float = 1.0
    corrected_CF: float = 0.0
    corrected_Isp: float = 0.0  # s


def estimate_boundary_layer_loss(
    throat_radius: float,
    nozzle_length: float,
    chamber_pressure: float,
) -> float:
    """Estimate fractional Isp loss due to boundary layer.

    Uses a simplified correlation based on Reynolds number at the throat.
    Typical losses are 0.5–2%.

    Args:
        throat_radius: Throat radius [m].
        nozzle_length: Nozzle axial length [m].
        chamber_pressure: Chamber pressure [Pa].

    Returns:
        Fractional loss (e.g. 0.01 for 1%).
    """
    # Simple engineering correlation:
    # loss ~ 0.01 * (1 + 0.5*L/Rt) * (2e6/Pc)^0.1
    # Higher Pc → lower relative BL loss; longer nozzle → more loss.
    L_Rt = nozzle_length / throat_radius
    loss = 0.005 * (1.0 + 0.1 * L_Rt) * (2.0e6 / max(chamber_pressure, 1e5)) ** 0.1
    return min(max(loss, 0.001), 0.05)  # clamp to 0.1%–5%


def compute_nozzle_efficiency(
    contour: NozzleContour,
    CF_ideal: float,
    Isp_ideal: float,
    chamber_pressure: float = 2.0e6,
) -> NozzleEfficiency:
    """Compute overall nozzle efficiency with loss breakdown.

    Args:
        contour: NozzleContour from conical/parabolic/MOC generator.
        CF_ideal: Ideal thrust coefficient.
        Isp_ideal: Ideal specific impulse [s].
        chamber_pressure: Chamber pressure [Pa] (for BL loss estimate).

    Returns:
        NozzleEfficiency with corrected performance.
    """
    div_eff = contour.divergence_efficiency
    bl_loss = estimate_boundary_layer_loss(
        contour.throat_radius, contour.length, chamber_pressure
    )

    total_eff = div_eff * (1.0 - bl_loss)

    return NozzleEfficiency(
        divergence_efficiency=div_eff,
        boundary_layer_loss=bl_loss,
        total_efficiency=total_eff,
        corrected_CF=CF_ideal * total_eff,
        corrected_Isp=Isp_ideal * total_eff,
    )


# --- Flow separation prediction ---


def summerfield_separation_pressure(pc: float, pa: float) -> float:
    """Summerfield criterion for flow separation.

    Flow separates when wall pressure drops below:
        p_sep ≈ 0.35–0.40 · pa

    Returns the approximate separation pressure [Pa].
    """
    return 0.37 * pa


def check_flow_separation(
    pe: float,
    pa: float,
) -> dict[str, float | bool]:
    """Check if flow separation occurs at the nozzle exit.

    Args:
        pe: Exit static pressure [Pa].
        pa: Ambient pressure [Pa].

    Returns:
        Dict with separation status and margin.
    """
    p_sep = summerfield_separation_pressure(0, pa)
    separated = pe < p_sep

    return {
        "separated": separated,
        "pe": pe,
        "pa": pa,
        "p_separation": p_sep,
        "margin": (pe - p_sep) / pa if pa > 0 else float("inf"),
    }
