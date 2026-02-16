"""Tests for the feed system sizing module."""

import math

import pytest

from resa_pro.core.feed_system import (
    PressureBudget,
    TankDesign,
    compute_pressure_budget,
    feed_line_pressure_drop,
    size_pressurant_blowdown,
    size_pressurant_regulated,
    size_tank,
)
from resa_pro.utils.constants import PI


class TestTankSizing:
    """Test propellant tank sizing."""

    def test_basic_tank(self):
        """Size a tank for 5 kg of ethanol at 30 bar."""
        result = size_tank(
            propellant_mass=5.0,
            propellant_density=789.0,
            tank_pressure=30e5,
            inner_diameter=0.15,
            material_yield_strength=276e6,
            material_density=2700.0,
        )

        assert isinstance(result, TankDesign)
        assert result.propellant_volume > 0
        assert result.total_volume > result.propellant_volume
        assert result.wall_thickness > 0
        assert result.tank_mass > 0
        assert result.cylinder_length >= 0

    def test_volume_includes_ullage(self):
        """Total volume should include ullage fraction."""
        result = size_tank(5.0, 789.0, 30e5, 0.15, 276e6, 2700.0, ullage_fraction=0.10)
        expected_V_prop = 5.0 / 789.0
        expected_V_total = expected_V_prop / 0.90
        assert result.total_volume == pytest.approx(expected_V_total, rel=1e-6)

    def test_higher_pressure_thicker_wall(self):
        """Higher tank pressure → thicker wall."""
        r1 = size_tank(5.0, 789.0, 20e5, 0.15, 276e6, 2700.0)
        r2 = size_tank(5.0, 789.0, 60e5, 0.15, 276e6, 2700.0)
        assert r2.wall_thickness > r1.wall_thickness

    def test_larger_diameter_shorter_cylinder(self):
        """Larger diameter → shorter cylinder for the same volume."""
        r1 = size_tank(5.0, 789.0, 30e5, 0.10, 276e6, 2700.0)
        r2 = size_tank(5.0, 789.0, 30e5, 0.20, 276e6, 2700.0)
        assert r2.cylinder_length < r1.cylinder_length

    def test_wall_thickness_formula(self):
        """Wall thickness should match thin-wall hoop stress formula."""
        P = 30e5
        Ri = 0.075
        SF = 2.0
        sigma_y = 276e6
        expected_t = P * Ri * SF / sigma_y
        result = size_tank(5.0, 789.0, P, 0.15, sigma_y, 2700.0, safety_factor=SF)
        assert result.wall_thickness == pytest.approx(expected_t, rel=1e-6)


class TestPressurantBlowdown:
    """Test blowdown pressurant sizing."""

    def test_basic_blowdown(self):
        result = size_pressurant_blowdown(
            tank_volume=0.010,
            tank_pressure=25e5,
            blowdown_ratio=3.0,
        )
        assert result.pressurant_mass > 0
        assert result.bottle_volume > 0
        assert result.bottle_pressure_initial > result.bottle_pressure_final
        assert result.blowdown_ratio == pytest.approx(3.0)

    def test_higher_blowdown_ratio_higher_initial_pressure(self):
        r1 = size_pressurant_blowdown(0.010, 25e5, blowdown_ratio=2.0)
        r2 = size_pressurant_blowdown(0.010, 25e5, blowdown_ratio=4.0)
        assert r2.bottle_pressure_initial > r1.bottle_pressure_initial

    def test_helium_lighter_than_nitrogen(self):
        """Helium pressurant should require less mass than nitrogen."""
        r_n2 = size_pressurant_blowdown(0.010, 25e5, pressurant_molar_mass=0.028)
        r_he = size_pressurant_blowdown(0.010, 25e5, pressurant_molar_mass=0.004)
        assert r_he.pressurant_mass < r_n2.pressurant_mass


class TestPressurantRegulated:
    """Test regulated pressurant sizing."""

    def test_basic_regulated(self):
        result = size_pressurant_regulated(
            tank_volume=0.010,
            regulated_pressure=25e5,
            bottle_pressure=300e5,
        )
        assert result.pressurant_mass > 0
        assert result.bottle_volume > 0
        assert result.bottle_pressure_initial == pytest.approx(300e5)

    def test_higher_regulated_pressure_more_gas(self):
        r1 = size_pressurant_regulated(0.010, 20e5, 300e5)
        r2 = size_pressurant_regulated(0.010, 40e5, 300e5)
        assert r2.pressurant_mass > r1.pressurant_mass


class TestFeedLine:
    """Test feed line pressure drop."""

    def test_positive_dp(self):
        result = feed_line_pressure_drop(
            mass_flow=0.5, rho=800, mu=1e-3,
            line_diameter=0.012, line_length=1.0,
        )
        assert result.total_dp > 0
        assert result.velocity > 0
        assert result.reynolds > 0

    def test_longer_line_higher_dp(self):
        r1 = feed_line_pressure_drop(0.5, 800, 1e-3, 0.012, 0.5)
        r2 = feed_line_pressure_drop(0.5, 800, 1e-3, 0.012, 2.0)
        assert r2.friction_dp > r1.friction_dp

    def test_larger_diameter_lower_dp(self):
        r1 = feed_line_pressure_drop(0.5, 800, 1e-3, 0.010, 1.0)
        r2 = feed_line_pressure_drop(0.5, 800, 1e-3, 0.025, 1.0)
        assert r2.total_dp < r1.total_dp

    def test_gravity_dp_positive_upward(self):
        """Positive height change (upward) → positive gravity ΔP."""
        result = feed_line_pressure_drop(0.5, 800, 1e-3, 0.012, 1.0, height_change=1.0)
        assert result.gravity_dp > 0

    def test_minor_losses(self):
        """Higher K-factor → higher minor losses."""
        r1 = feed_line_pressure_drop(0.5, 800, 1e-3, 0.012, 1.0, K_minor=2.0)
        r2 = feed_line_pressure_drop(0.5, 800, 1e-3, 0.012, 1.0, K_minor=10.0)
        assert r2.minor_dp > r1.minor_dp


class TestPressureBudget:
    """Test system-level pressure budget."""

    def test_basic_budget(self):
        result = compute_pressure_budget(
            chamber_pressure=2e6,
            injector_dp=4e5,
        )
        assert isinstance(result, PressureBudget)
        assert result.required_tank_pressure > 2e6 + 4e5

    def test_budget_includes_all_losses(self):
        result = compute_pressure_budget(
            chamber_pressure=2e6,
            injector_dp=4e5,
            feed_line_dp=1e5,
            cooling_dp=2e5,
            valve_dp=5e4,
            margin_fraction=0.0,
        )
        expected = 2e6 + 4e5 + 1e5 + 2e5 + 5e4
        assert result.required_tank_pressure == pytest.approx(expected, rel=1e-6)

    def test_margin_adds_pressure(self):
        r1 = compute_pressure_budget(2e6, 4e5, margin_fraction=0.0)
        r2 = compute_pressure_budget(2e6, 4e5, margin_fraction=0.10)
        assert r2.required_tank_pressure > r1.required_tank_pressure
