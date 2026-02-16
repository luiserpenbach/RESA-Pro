"""Tests for the regenerative cooling module."""

import math

import numpy as np
import pytest

from resa_pro.core.cooling import (
    CoolingChannel,
    analyze_regen_cooling,
    channel_pressure_drop,
    coolant_htc_dittus_boelter,
    coolant_htc_sieder_tate,
    size_channels,
)
from resa_pro.utils.constants import PI


class TestCoolingChannel:
    """Test CoolingChannel geometry calculations."""

    def test_area(self):
        ch = CoolingChannel(width=1e-3, height=2e-3)
        assert ch.area == pytest.approx(2e-6, rel=1e-6)

    def test_wetted_perimeter(self):
        ch = CoolingChannel(width=1e-3, height=2e-3)
        assert ch.wetted_perimeter == pytest.approx(6e-3, rel=1e-6)

    def test_hydraulic_diameter(self):
        ch = CoolingChannel(width=1e-3, height=2e-3)
        Dh = 4 * 2e-6 / 6e-3
        assert ch.hydraulic_diameter == pytest.approx(Dh, rel=1e-6)

    def test_total_flow_area(self):
        ch = CoolingChannel(width=1e-3, height=2e-3, n_channels=40)
        assert ch.total_flow_area == pytest.approx(40 * 2e-6, rel=1e-6)


class TestSizeChannels:
    """Test automatic channel count sizing."""

    def test_positive_channel_count(self):
        ch = size_channels(local_radius=0.030, channel_width=1e-3, fin_width=1e-3)
        assert ch.n_channels > 0

    def test_smaller_radius_fewer_channels(self):
        ch_large = size_channels(local_radius=0.050)
        ch_small = size_channels(local_radius=0.015)
        assert ch_large.n_channels > ch_small.n_channels

    def test_wider_pitch_fewer_channels(self):
        ch_narrow = size_channels(0.030, channel_width=0.5e-3, fin_width=0.5e-3)
        ch_wide = size_channels(0.030, channel_width=2.0e-3, fin_width=2.0e-3)
        assert ch_narrow.n_channels > ch_wide.n_channels


class TestHeatTransferCorrelations:
    """Test coolant-side HTC correlations."""

    def test_dittus_boelter_positive(self):
        h = coolant_htc_dittus_boelter(Re=50000, Pr=7.0, k=0.6, Dh=2e-3)
        assert h > 0

    def test_dittus_boelter_increases_with_Re(self):
        h1 = coolant_htc_dittus_boelter(Re=10000, Pr=7.0, k=0.6, Dh=2e-3)
        h2 = coolant_htc_dittus_boelter(Re=50000, Pr=7.0, k=0.6, Dh=2e-3)
        assert h2 > h1

    def test_sieder_tate_positive(self):
        h = coolant_htc_sieder_tate(
            Re=50000, Pr=7.0, k=0.6, Dh=2e-3,
            mu_bulk=1e-3, mu_wall=0.5e-3,
        )
        assert h > 0

    def test_sieder_tate_viscosity_correction(self):
        """Lower wall viscosity (hotter wall) → higher HTC."""
        h1 = coolant_htc_sieder_tate(50000, 7.0, 0.6, 2e-3, 1e-3, 1e-3)
        h2 = coolant_htc_sieder_tate(50000, 7.0, 0.6, 2e-3, 1e-3, 0.3e-3)
        assert h2 > h1


class TestPressureDrop:
    """Test channel pressure drop calculations."""

    def test_positive_pressure_drop(self):
        dp = channel_pressure_drop(
            length=0.1, Dh=2e-3, rho=800, velocity=10.0, Re=30000,
        )
        assert dp > 0

    def test_longer_channel_higher_dp(self):
        dp1 = channel_pressure_drop(0.05, 2e-3, 800, 10.0, 30000)
        dp2 = channel_pressure_drop(0.20, 2e-3, 800, 10.0, 30000)
        assert dp2 > dp1

    def test_higher_velocity_higher_dp(self):
        dp1 = channel_pressure_drop(0.1, 2e-3, 800, 5.0, 15000)
        dp2 = channel_pressure_drop(0.1, 2e-3, 800, 20.0, 60000)
        assert dp2 > dp1


class TestRegenCoolingAnalysis:
    """Test the full regen cooling analysis."""

    def _make_contour(self):
        """Create a simple test contour (converging section)."""
        x = np.linspace(0, 0.1, 50)
        # Linearly converge from R=0.03 to R=0.015 (throat)
        y = np.linspace(0.030, 0.015, 50)
        return x, y

    def test_basic_analysis(self):
        x, y = self._make_contour()
        result = analyze_regen_cooling(
            contour_x=x,
            contour_y=y,
            throat_radius=0.015,
            pc=2e6,
            c_star=1550,
            Tc=3100,
            gamma=1.21,
            molar_mass=0.026,
            coolant_mass_flow=0.2,
            coolant_inlet_temp=293.0,
            coolant_cp=2440.0,
            coolant_rho=789.0,
            coolant_mu=1.2e-3,
            coolant_k=0.17,
            wall_conductivity=350.0,
        )

        assert len(result.stations) == 50
        assert result.max_wall_temperature > 300
        assert result.max_heat_flux > 0
        assert result.total_pressure_drop >= 0
        assert result.coolant_outlet_temperature >= 293.0

    def test_counter_flow_heats_coolant(self):
        """Coolant outlet temperature should be higher than inlet."""
        x, y = self._make_contour()
        result = analyze_regen_cooling(
            contour_x=x, contour_y=y,
            throat_radius=0.015, pc=2e6, c_star=1550, Tc=3100,
            gamma=1.21, molar_mass=0.026,
            coolant_mass_flow=0.2, coolant_inlet_temp=293.0,
            coolant_cp=2440.0, coolant_rho=789.0,
            coolant_mu=1.2e-3, coolant_k=0.17,
            wall_conductivity=350.0,
            counter_flow=True,
        )
        assert result.coolant_outlet_temperature > 293.0

    def test_higher_wall_k_lower_wall_temp(self):
        """Higher wall conductivity → lower gas-side wall temperature."""
        x, y = self._make_contour()
        kwargs = dict(
            contour_x=x, contour_y=y,
            throat_radius=0.015, pc=2e6, c_star=1550, Tc=3100,
            gamma=1.21, molar_mass=0.026,
            coolant_mass_flow=0.2, coolant_inlet_temp=293.0,
            coolant_cp=2440.0, coolant_rho=789.0,
            coolant_mu=1.2e-3, coolant_k=0.17,
        )
        r_copper = analyze_regen_cooling(**kwargs, wall_conductivity=350.0)
        r_steel = analyze_regen_cooling(**kwargs, wall_conductivity=16.0)
        assert r_copper.max_wall_temperature < r_steel.max_wall_temperature
