"""Tests for the nozzle contour generation module."""

import math

import numpy as np
import pytest

from resa_pro.core.nozzle import (
    NozzleMethod,
    check_flow_separation,
    compute_nozzle_efficiency,
    conical_nozzle,
    estimate_boundary_layer_loss,
    parabolic_nozzle,
)
from resa_pro.utils.constants import RAD_TO_DEG


class TestConicalNozzle:
    """Test conical nozzle generation."""

    def test_basic_conical(self):
        contour = conical_nozzle(
            throat_radius=0.015,
            expansion_ratio=10,
            half_angle=15.0,
        )
        assert contour.method == NozzleMethod.CONICAL
        assert contour.expansion_ratio == 10.0

        # Exit radius: Rt * sqrt(eps)
        expected_Re = 0.015 * math.sqrt(10)
        assert contour.exit_radius == pytest.approx(expected_Re, rel=1e-4)

        # Contour arrays populated
        assert len(contour.x) > 50
        assert len(contour.x) == len(contour.y)

        # First point near throat, last near exit
        assert contour.y[0] == pytest.approx(0.015, rel=0.1)
        assert contour.y[-1] == pytest.approx(expected_Re, rel=0.01)

    def test_divergence_efficiency(self):
        """λ = (1 + cos(α)) / 2."""
        contour = conical_nozzle(0.015, 10, half_angle=15.0)
        expected = (1 + math.cos(math.radians(15))) / 2
        assert contour.divergence_efficiency == pytest.approx(expected, rel=1e-6)

    def test_steeper_angle_shorter_nozzle(self):
        """Higher half-angle → shorter nozzle."""
        c15 = conical_nozzle(0.015, 10, half_angle=15.0)
        c30 = conical_nozzle(0.015, 10, half_angle=30.0)
        assert c30.length < c15.length

    def test_steeper_angle_lower_efficiency(self):
        """Higher half-angle → lower divergence efficiency."""
        c15 = conical_nozzle(0.015, 10, half_angle=15.0)
        c30 = conical_nozzle(0.015, 10, half_angle=30.0)
        assert c30.divergence_efficiency < c15.divergence_efficiency


class TestParabolicNozzle:
    """Test parabolic (Rao) nozzle generation."""

    def test_basic_parabolic(self):
        contour = parabolic_nozzle(
            throat_radius=0.015,
            expansion_ratio=10,
            fractional_length=0.8,
        )
        assert contour.method == NozzleMethod.PARABOLIC
        expected_Re = 0.015 * math.sqrt(10)
        assert contour.exit_radius == pytest.approx(expected_Re, rel=1e-4)

    def test_shorter_than_conical(self):
        """80% Rao nozzle should be shorter than 15° conical."""
        conical = conical_nozzle(0.015, 10, half_angle=15.0)
        parabolic = parabolic_nozzle(0.015, 10, fractional_length=0.8)
        assert parabolic.length < conical.length

    def test_good_divergence_efficiency(self):
        """Parabolic nozzle should have high divergence efficiency (>0.98)."""
        parabolic = parabolic_nozzle(0.015, 10, fractional_length=0.8)
        assert parabolic.divergence_efficiency > 0.98

    def test_contour_monotonic_radius(self):
        """Radius should monotonically increase from throat to exit."""
        contour = parabolic_nozzle(0.015, 10)
        # Allow small dips in the arc region
        for i in range(len(contour.y) // 4, len(contour.y) - 1):
            assert contour.y[i + 1] >= contour.y[i] - 1e-8


class TestNozzleEfficiency:
    """Test nozzle efficiency calculations."""

    def test_boundary_layer_loss_range(self):
        loss = estimate_boundary_layer_loss(0.015, 0.15, 2e6)
        assert 0.001 < loss < 0.05

    def test_higher_pc_lower_bl_loss(self):
        loss_low = estimate_boundary_layer_loss(0.015, 0.15, 1e6)
        loss_high = estimate_boundary_layer_loss(0.015, 0.15, 5e6)
        assert loss_high < loss_low

    def test_total_efficiency_less_than_1(self):
        contour = conical_nozzle(0.015, 10)
        eff = compute_nozzle_efficiency(contour, CF_ideal=1.5, Isp_ideal=280, chamber_pressure=2e6)
        assert eff.total_efficiency < 1.0
        assert eff.corrected_CF < 1.5
        assert eff.corrected_Isp < 280


class TestFlowSeparation:
    """Test flow separation prediction."""

    def test_no_separation_at_design(self):
        """High pe should not cause separation."""
        result = check_flow_separation(pe=50000, pa=101325)
        assert not result["separated"]

    def test_separation_at_low_pe(self):
        """Very low pe should trigger separation."""
        result = check_flow_separation(pe=5000, pa=101325)
        assert result["separated"]
