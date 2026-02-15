"""Interpolation helpers for RESA Pro."""

from __future__ import annotations

import numpy as np
from scipy import interpolate


def linear_interp_1d(
    x: np.ndarray,
    y: np.ndarray,
    x_new: float | np.ndarray,
    extrapolate: bool = False,
) -> float | np.ndarray:
    """One-dimensional linear interpolation.

    Args:
        x: Known x-coordinates (must be monotonically increasing).
        y: Known y-values.
        x_new: Query point(s).
        extrapolate: If True, allow extrapolation beyond data range.

    Returns:
        Interpolated value(s).
    """
    fill = "extrapolate" if extrapolate else (y[0], y[-1])
    f = interpolate.interp1d(x, y, kind="linear", fill_value=fill, bounds_error=False)
    return float(f(x_new)) if np.isscalar(x_new) else f(x_new)


def cubic_interp_1d(
    x: np.ndarray,
    y: np.ndarray,
    x_new: float | np.ndarray,
) -> float | np.ndarray:
    """One-dimensional cubic spline interpolation."""
    cs = interpolate.CubicSpline(x, y)
    result = cs(x_new)
    return float(result) if np.isscalar(x_new) else result


def smooth_contour(
    x: np.ndarray,
    y: np.ndarray,
    num_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """Re-sample a 2-D contour onto a smooth cubic spline.

    Useful for refining chamber/nozzle contour points.

    Args:
        x: Axial coordinates.
        y: Radial coordinates.
        num_points: Number of output points.

    Returns:
        Tuple of (x_smooth, y_smooth) arrays.
    """
    # Parametrise by arc length
    dx = np.diff(x)
    dy = np.diff(y)
    ds = np.sqrt(dx**2 + dy**2)
    s = np.concatenate([[0], np.cumsum(ds)])
    s_new = np.linspace(0, s[-1], num_points)

    x_smooth = cubic_interp_1d(s, x, s_new)
    y_smooth = cubic_interp_1d(s, y, s_new)
    return x_smooth, y_smooth
