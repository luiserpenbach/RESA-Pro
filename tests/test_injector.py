"""Tests for the injector design module."""

import math

import pytest

from resa_pro.core.injector import (
    InjectorDesign,
    check_chugging_stability,
    design_injector,
    injection_velocity,
    orifice_area_from_flow,
    orifice_mass_flow,
    stability_margin,
)
from resa_pro.utils.constants import PI


class TestOrificeEquations:
    """Test basic orifice flow equations."""

    def test_mass_flow_positive(self):
        """Mass flow should be positive for positive inputs."""
        mdot = orifice_mass_flow(cd=0.65, area=1e-6, dp=5e5, rho=1000)
        assert mdot > 0

    def test_mass_flow_increases_with_dp(self):
        """Higher ΔP → higher mass flow."""
        m1 = orifice_mass_flow(0.65, 1e-6, 1e5, 1000)
        m2 = orifice_mass_flow(0.65, 1e-6, 4e5, 1000)
        assert m2 > m1

    def test_mass_flow_increases_with_area(self):
        """Larger area → higher mass flow."""
        m1 = orifice_mass_flow(0.65, 1e-6, 1e5, 1000)
        m2 = orifice_mass_flow(0.65, 2e-6, 1e5, 1000)
        assert m2 > m1

    def test_area_from_flow_roundtrip(self):
        """orifice_area_from_flow should be the inverse of orifice_mass_flow."""
        A = 1.5e-6
        cd = 0.65
        dp = 4e5
        rho = 800.0
        mdot = orifice_mass_flow(cd, A, dp, rho)
        A_calc = orifice_area_from_flow(mdot, cd, dp, rho)
        assert A_calc == pytest.approx(A, rel=1e-6)

    def test_injection_velocity_positive(self):
        v = injection_velocity(0.65, 4e5, 800)
        assert v > 0

    def test_injection_velocity_increases_with_dp(self):
        v1 = injection_velocity(0.65, 1e5, 800)
        v2 = injection_velocity(0.65, 4e5, 800)
        assert v2 > v1


class TestInjectorDesign:
    """Test the design_injector function."""

    def test_basic_design(self):
        """Design an injector for typical conditions."""
        result = design_injector(
            mass_flow=1.0,
            mixture_ratio=4.0,
            chamber_pressure=2e6,
            rho_oxidizer=1220.0,
            rho_fuel=789.0,
        )

        assert isinstance(result, InjectorDesign)
        # Mass flow split should be correct
        assert result.mass_flow_oxidizer == pytest.approx(0.8, rel=1e-6)
        assert result.mass_flow_fuel == pytest.approx(0.2, rel=1e-6)

        # Element counts should be reasonable
        assert result.n_elements_ox >= 1
        assert result.n_elements_fuel >= 1

        # Orifice diameters should be small positive values
        assert 0 < result.element_ox.diameter < 0.01
        assert 0 < result.element_fuel.diameter < 0.01

        # Manifold pressures should be above chamber pressure
        assert result.manifold_pressure_ox > 2e6
        assert result.manifold_pressure_fuel > 2e6

    def test_mass_flow_conservation(self):
        """Oxidizer + fuel mass flow should equal total."""
        result = design_injector(
            mass_flow=1.5,
            mixture_ratio=3.0,
            chamber_pressure=2e6,
            rho_oxidizer=1220.0,
            rho_fuel=789.0,
        )
        total = result.mass_flow_oxidizer + result.mass_flow_fuel
        assert total == pytest.approx(1.5, rel=1e-6)

    def test_fixed_element_count(self):
        """When n_elements is specified, it should be honoured."""
        result = design_injector(
            mass_flow=1.0,
            mixture_ratio=4.0,
            chamber_pressure=2e6,
            rho_oxidizer=1220.0,
            rho_fuel=789.0,
            n_elements_ox=12,
            n_elements_fuel=12,
        )
        assert result.n_elements_ox == 12
        assert result.n_elements_fuel == 12

    def test_higher_dp_fraction(self):
        """Higher ΔP fraction → higher manifold pressure."""
        r1 = design_injector(1.0, 4.0, 2e6, 1220, 789, dp_fraction=0.15)
        r2 = design_injector(1.0, 4.0, 2e6, 1220, 789, dp_fraction=0.30)
        assert r2.manifold_pressure_ox > r1.manifold_pressure_ox

    def test_momentum_ratio_positive(self):
        result = design_injector(1.0, 4.0, 2e6, 1220, 789)
        assert result.momentum_ratio > 0


class TestStability:
    """Test stability checking functions."""

    def test_stability_margin(self):
        margin = stability_margin(4e5, 2e6)
        assert margin == pytest.approx(0.2, rel=1e-6)

    def test_chugging_stable(self):
        result = check_chugging_stability(0.20, min_margin=0.15)
        assert result["stable"] is True

    def test_chugging_unstable(self):
        result = check_chugging_stability(0.10, min_margin=0.15)
        assert result["stable"] is False
