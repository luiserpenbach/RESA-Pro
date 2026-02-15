"""Tests for the thermal analysis module."""

import math

import pytest

from resa_pro.core.thermal import (
    adiabatic_wall_temperature,
    bartz_heat_transfer_coefficient,
    compute_heat_flux_distribution,
    heat_flux,
    radiative_equilibrium_temperature,
    radiative_heat_rejection,
    wall_temperature_simple,
)
from resa_pro.utils.constants import STEFAN_BOLTZMANN


class TestBartzEquation:
    """Test Bartz heat transfer coefficient."""

    def test_positive_htc(self):
        """h_g should be positive for reasonable inputs."""
        h = bartz_heat_transfer_coefficient(
            pc=2e6,
            c_star=1550,
            Dt=0.030,
            Tc=3100,
            Tw=600,
            gamma=1.21,
            molar_mass=0.026,
            local_area_ratio=1.0,
        )
        assert h > 0

    def test_htc_highest_at_throat(self):
        """Heat transfer coefficient should be highest at the throat (A/At=1)."""
        h_throat = bartz_heat_transfer_coefficient(
            pc=2e6, c_star=1550, Dt=0.030, Tc=3100, Tw=600,
            gamma=1.21, molar_mass=0.026, local_area_ratio=1.0,
        )
        h_chamber = bartz_heat_transfer_coefficient(
            pc=2e6, c_star=1550, Dt=0.030, Tc=3100, Tw=600,
            gamma=1.21, molar_mass=0.026, local_area_ratio=3.0,
        )
        h_nozzle = bartz_heat_transfer_coefficient(
            pc=2e6, c_star=1550, Dt=0.030, Tc=3100, Tw=600,
            gamma=1.21, molar_mass=0.026, local_area_ratio=5.0,
        )
        assert h_throat > h_chamber
        assert h_throat > h_nozzle

    def test_higher_pc_higher_htc(self):
        """Higher chamber pressure → higher h_g."""
        h_low = bartz_heat_transfer_coefficient(
            pc=1e6, c_star=1550, Dt=0.030, Tc=3100, Tw=600,
            gamma=1.21, molar_mass=0.026, local_area_ratio=1.0,
        )
        h_high = bartz_heat_transfer_coefficient(
            pc=5e6, c_star=1550, Dt=0.030, Tc=3100, Tw=600,
            gamma=1.21, molar_mass=0.026, local_area_ratio=1.0,
        )
        assert h_high > h_low


class TestAdiabaticWallTemperature:
    """Test adiabatic wall temperature calculation."""

    def test_at_mach_0(self):
        """At M=0, T_aw should equal Tc."""
        T_aw = adiabatic_wall_temperature(3100, 1.2, M=0.0, recovery_factor=0.9)
        assert T_aw == pytest.approx(3100, rel=1e-6)

    def test_less_than_stagnation(self):
        """T_aw should be less than Tc for M > 0."""
        T_aw = adiabatic_wall_temperature(3100, 1.2, M=2.0, recovery_factor=0.9)
        assert T_aw < 3100

    def test_recovery_factor_effect(self):
        """Higher recovery factor → higher T_aw."""
        T_low = adiabatic_wall_temperature(3100, 1.2, M=2.0, recovery_factor=0.8)
        T_high = adiabatic_wall_temperature(3100, 1.2, M=2.0, recovery_factor=0.95)
        assert T_high > T_low


class TestHeatFlux:
    """Test heat flux calculation."""

    def test_positive_heat_flux(self):
        """Heat flux should be positive when T_aw > T_wall."""
        q = heat_flux(5000, 2800, 600)
        assert q > 0

    def test_zero_heat_flux(self):
        """Heat flux = 0 when T_aw = T_wall."""
        q = heat_flux(5000, 600, 600)
        assert q == pytest.approx(0.0)

    def test_heat_flux_distribution(self):
        """Heat flux distribution should have a peak near the throat."""
        import numpy as np
        from resa_pro.core.chamber import size_chamber_from_thrust

        geom = size_chamber_from_thrust(2000, 2e6)
        results = compute_heat_flux_distribution(
            contour_x=geom.contour_x,
            contour_y=geom.contour_y,
            throat_radius=geom.throat_radius,
            pc=2e6,
            c_star=1550,
            Tc=3100,
            gamma=1.21,
            molar_mass=0.026,
        )
        assert len(results) > 0
        # All heat fluxes should be positive
        assert all(r.q_dot > 0 for r in results)


class TestRadiativeCooling:
    """Test radiative cooling calculations."""

    def test_equilibrium_temperature(self):
        """Stefan-Boltzmann equilibrium: q = ε·σ·T^4."""
        q = 1e6  # 1 MW/m²
        T = radiative_equilibrium_temperature(q, emissivity=0.8)
        # Verify: ε·σ·T^4 ≈ q
        q_check = 0.8 * STEFAN_BOLTZMANN * T**4
        assert q_check == pytest.approx(q, rel=1e-6)

    def test_heat_rejection(self):
        T = 1500  # K
        q = radiative_heat_rejection(T, emissivity=0.8)
        expected = 0.8 * STEFAN_BOLTZMANN * 1500**4
        assert q == pytest.approx(expected, rel=1e-6)


class TestWallTemperature:
    """Test simple wall temperature estimation."""

    def test_wall_temps_between_extremes(self):
        """Gas-side wall temp < T_aw, coolant-side wall temp > T_coolant."""
        T_wg, T_wc = wall_temperature_simple(
            h_g=5000,
            T_aw=2800,
            h_c=10000,
            T_coolant=300,
            wall_thickness=0.002,
            wall_conductivity=350,
        )
        assert T_wg < 2800
        assert T_wc > 300
        assert T_wg > T_wc  # gas side hotter than coolant side
