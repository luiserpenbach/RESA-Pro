"""Tests for the Method of Characteristics solver."""

import math

import numpy as np
import pytest

from resa_pro.core.moc import (
    compute_moc_nozzle,
    mach_angle,
    mach_from_prandtl_meyer,
    prandtl_meyer,
)


class TestPrandtlMeyer:
    """Test Prandtl-Meyer function."""

    def test_at_mach_1(self):
        """ν(1) = 0."""
        assert prandtl_meyer(1.0, 1.4) == pytest.approx(0.0)

    def test_subsonic_returns_zero(self):
        assert prandtl_meyer(0.5, 1.4) == 0.0

    def test_known_value(self):
        """ν(M=2, γ=1.4) ≈ 26.38° = 0.4604 rad."""
        nu = prandtl_meyer(2.0, 1.4)
        assert nu == pytest.approx(math.radians(26.38), rel=1e-2)

    def test_round_trip(self):
        """Inversion should recover original Mach number."""
        for M in [1.5, 2.0, 3.0, 5.0]:
            nu = prandtl_meyer(M, 1.4)
            M_inv = mach_from_prandtl_meyer(nu, 1.4)
            assert M_inv == pytest.approx(M, rel=1e-6)


class TestMachAngle:
    """Test Mach angle calculation."""

    def test_at_mach_1(self):
        assert mach_angle(1.0) == pytest.approx(math.pi / 2, rel=1e-6)

    def test_at_mach_2(self):
        assert mach_angle(2.0) == pytest.approx(math.radians(30), rel=1e-3)


class TestMOCSolver:
    """Test MOC nozzle solver."""

    def test_basic_moc(self):
        """MOC should produce a valid nozzle contour."""
        result = compute_moc_nozzle(
            throat_radius=0.015,
            expansion_ratio=5.0,
            gamma=1.4,
            num_char_lines=10,
        )
        assert result.exit_mach > 2.0
        assert len(result.wall_x) > 2
        assert len(result.wall_y) > 2
        # Wall starts at throat radius
        assert result.wall_y[0] == pytest.approx(0.015, abs=0.001)
        # Wall ends at exit radius
        expected_Re = 0.015 * math.sqrt(5.0)
        assert result.wall_y[-1] == pytest.approx(expected_Re, rel=0.05)

    def test_length_positive(self):
        result = compute_moc_nozzle(0.015, 5.0, 1.4, num_char_lines=10)
        assert result.length > 0

    def test_more_lines_smoother(self):
        """More characteristic lines should produce more wall points."""
        r10 = compute_moc_nozzle(0.015, 5.0, 1.4, num_char_lines=10)
        r20 = compute_moc_nozzle(0.015, 5.0, 1.4, num_char_lines=20)
        assert len(r20.wall_x) >= len(r10.wall_x)
