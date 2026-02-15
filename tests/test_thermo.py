"""Tests for the thermodynamics module."""

import math

import pytest

from resa_pro.core.thermo import (
    area_ratio_from_mach,
    characteristic_velocity,
    compute_nozzle_performance,
    exit_pressure_ratio,
    lookup_combustion,
    mach_from_area_ratio,
    mass_flow_rate,
    pressure_ratio,
    specific_impulse,
    temperature_ratio,
    throat_area,
    thrust_coefficient,
)
from resa_pro.utils.constants import G_0, R_UNIVERSAL


class TestIsentropicRelations:
    """Test isentropic flow relations."""

    def test_area_ratio_at_mach_1(self):
        """A/A* should be 1.0 at M = 1."""
        assert area_ratio_from_mach(1.0, 1.4) == pytest.approx(1.0, abs=1e-10)

    def test_area_ratio_supersonic(self):
        """A/A* for M=2, γ=1.4 should be ~1.6875."""
        ar = area_ratio_from_mach(2.0, 1.4)
        assert ar == pytest.approx(1.6875, rel=1e-4)

    def test_mach_from_area_ratio_supersonic(self):
        """Inversion should recover M=2 from A/A*=1.6875."""
        M = mach_from_area_ratio(1.6875, 1.4, supersonic=True)
        assert M == pytest.approx(2.0, rel=1e-3)

    def test_mach_from_area_ratio_subsonic(self):
        """Subsonic solution for A/A*=1.6875 should be ~0.3725."""
        M = mach_from_area_ratio(1.6875, 1.4, supersonic=False)
        assert 0.0 < M < 1.0

    def test_area_ratio_round_trip(self):
        """Computing A/A* then inverting should recover original M."""
        for M in [1.5, 3.0, 5.0, 10.0]:
            ar = area_ratio_from_mach(M, 1.4)
            M_recovered = mach_from_area_ratio(ar, 1.4, supersonic=True)
            assert M_recovered == pytest.approx(M, rel=1e-6)

    def test_pressure_ratio_at_mach_0(self):
        """P/P0 = 1.0 at M=0."""
        assert pressure_ratio(0.0, 1.4) == pytest.approx(1.0)

    def test_pressure_ratio_at_mach_1(self):
        """P/P0 at M=1, γ=1.4 should be ~0.5283."""
        p = pressure_ratio(1.0, 1.4)
        assert p == pytest.approx(0.5283, rel=1e-3)

    def test_temperature_ratio_at_mach_1(self):
        """T/T0 at M=1, γ=1.4 should be ~0.8333."""
        t = temperature_ratio(1.0, 1.4)
        assert t == pytest.approx(0.8333, rel=1e-3)


class TestPerformanceParameters:
    """Test c*, CF, Isp calculations."""

    def test_characteristic_velocity(self):
        """c* for typical LOX/RP-1 conditions."""
        gamma = 1.2
        M_mol = 0.023  # kg/mol
        R_spec = R_UNIVERSAL / M_mol
        Tc = 3500.0  # K
        c_s = characteristic_velocity(gamma, R_spec, Tc)
        # c* should be in the range 1600–1900 m/s for LOX/RP-1
        assert 1500 < c_s < 2000

    def test_thrust_coefficient_vacuum(self):
        """CF in vacuum should be higher than at sea level."""
        gamma = 1.2
        eps = 10.0
        pe_pc = exit_pressure_ratio(gamma, eps)
        CF_vac = thrust_coefficient(gamma, eps, pe_pc, pa_pc=0.0)
        CF_sl = thrust_coefficient(gamma, eps, pe_pc, pa_pc=101325 / 2e6)
        assert CF_vac > CF_sl
        assert CF_vac > 1.0

    def test_specific_impulse(self):
        """Isp = c* · CF / g0."""
        c_star = 1700.0
        CF = 1.5
        isp = specific_impulse(c_star, CF)
        expected = c_star * CF / G_0
        assert isp == pytest.approx(expected, rel=1e-10)

    def test_throat_area(self):
        """At = F / (CF · Pc)."""
        F = 5000.0  # N
        Pc = 2e6  # Pa
        CF = 1.5
        At = throat_area(F, Pc, CF)
        assert At == pytest.approx(F / (CF * Pc), rel=1e-10)

    def test_mass_flow_rate(self):
        """mdot = Pc · At / c*."""
        Pc = 2e6
        At = 1e-3
        c_star = 1700.0
        mdot = mass_flow_rate(Pc, At, c_star)
        assert mdot == pytest.approx(Pc * At / c_star, rel=1e-10)


class TestNozzlePerformance:
    """Test complete nozzle performance computation."""

    def test_compute_nozzle_performance_n2o_ethanol(self):
        """Compute performance for N2O/ethanol at 20 bar."""
        perf = compute_nozzle_performance(
            gamma=1.21,
            molar_mass=0.026,
            Tc=3100,
            expansion_ratio=10,
            pc=2e6,
        )
        # Sanity checks
        assert perf.exit_mach > 2.0
        assert perf.Isp_vac > 200
        assert perf.Isp_vac > perf.Isp_sl
        assert perf.CF_vac > perf.CF_sl
        assert 0 < perf.pe_pc < 1
        assert perf.c_star > 1000

    def test_higher_expansion_ratio_increases_vacuum_isp(self):
        """Higher expansion ratio → higher vacuum Isp."""
        perf_10 = compute_nozzle_performance(1.2, 0.025, 3000, 10, 2e6)
        perf_50 = compute_nozzle_performance(1.2, 0.025, 3000, 50, 2e6)
        assert perf_50.Isp_vac > perf_10.Isp_vac


class TestCombustionLookup:
    """Test combustion data lookup."""

    def test_lookup_n2o_ethanol(self):
        comb = lookup_combustion("n2o", "ethanol")
        assert comb.c_star > 0
        assert comb.gamma > 1.0
        assert comb.chamber_temperature > 2000

    def test_lookup_with_mr(self):
        comb = lookup_combustion("n2o", "ethanol", mixture_ratio=4.0)
        assert comb.mixture_ratio == pytest.approx(4.0)

    def test_lookup_missing_raises(self):
        with pytest.raises(KeyError):
            lookup_combustion("xenon", "lithium")
