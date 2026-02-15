"""Tests for utility modules."""

import math

import numpy as np
import pytest

from resa_pro.utils.constants import G_0, P_ATM, R_UNIVERSAL, BAR_TO_PA
from resa_pro.utils.interpolation import cubic_interp_1d, linear_interp_1d, smooth_contour
from resa_pro.utils.units import (
    convert,
    force_to_si,
    length_to_si,
    pressure_from_si,
    pressure_to_si,
    temperature_to_si,
)
from resa_pro.utils.validation import (
    Severity,
    ValidationResult,
    validate_chamber_design,
    validate_positive,
    validate_range,
)


class TestConstants:
    def test_g0(self):
        assert G_0 == pytest.approx(9.80665)

    def test_p_atm(self):
        assert P_ATM == pytest.approx(101325.0)

    def test_r_universal(self):
        assert R_UNIVERSAL == pytest.approx(8.314, rel=1e-3)

    def test_bar_conversion(self):
        assert BAR_TO_PA == pytest.approx(1e5)


class TestUnits:
    def test_pressure_bar_to_pa(self):
        assert pressure_to_si(1.0, "bar") == pytest.approx(1e5, rel=1e-4)

    def test_pressure_psi_to_pa(self):
        assert pressure_to_si(14.696, "psi") == pytest.approx(101325, rel=1e-2)

    def test_pressure_round_trip(self):
        pa = pressure_to_si(20.0, "bar")
        bar = pressure_from_si(pa, "bar")
        assert bar == pytest.approx(20.0, rel=1e-6)

    def test_temperature_celsius_to_kelvin(self):
        assert temperature_to_si(0, "degC") == pytest.approx(273.15, rel=1e-4)

    def test_length_mm_to_m(self):
        assert length_to_si(25.4, "mm") == pytest.approx(0.0254, rel=1e-4)

    def test_force_lbf_to_n(self):
        assert force_to_si(1.0, "lbf") == pytest.approx(4.448, rel=1e-2)

    def test_convert_generic(self):
        assert convert(1.0, "km", "m") == pytest.approx(1000.0, rel=1e-6)


class TestInterpolation:
    def test_linear_exact(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([0, 2, 4, 6], dtype=float)
        assert linear_interp_1d(x, y, 1.5) == pytest.approx(3.0)

    def test_linear_boundary(self):
        x = np.array([0, 1, 2], dtype=float)
        y = np.array([10, 20, 30], dtype=float)
        assert linear_interp_1d(x, y, 0) == pytest.approx(10.0)

    def test_cubic(self):
        x = np.array([0, 1, 2, 3, 4], dtype=float)
        y = x**2
        # Cubic spline should closely match x^2
        assert cubic_interp_1d(x, y, 2.5) == pytest.approx(6.25, rel=0.1)

    def test_smooth_contour(self):
        x = np.array([0, 1, 2, 3], dtype=float)
        y = np.array([0, 0.5, 0.8, 1.0], dtype=float)
        xs, ys = smooth_contour(x, y, num_points=50)
        assert len(xs) == 50
        assert xs[0] == pytest.approx(0.0, abs=0.01)
        assert xs[-1] == pytest.approx(3.0, abs=0.01)


class TestValidation:
    def test_valid_design(self):
        design = {
            "chamber_pressure": 2e6,
            "thrust": 2000,
            "throat_diameter": 0.030,
            "contraction_ratio": 3.0,
            "l_star": 1.2,
            "expansion_ratio": 10.0,
        }
        result = validate_chamber_design(design)
        assert result.is_valid

    def test_negative_pressure_error(self):
        design = {"chamber_pressure": -1e6}
        result = validate_chamber_design(design)
        assert not result.is_valid

    def test_very_high_pressure_warning(self):
        design = {"chamber_pressure": 35e6}
        result = validate_chamber_design(design)
        assert result.has_warnings

    def test_contraction_ratio_below_1(self):
        design = {"contraction_ratio": 0.5}
        result = validate_chamber_design(design)
        assert not result.is_valid

    def test_validate_positive(self):
        result = ValidationResult()
        validate_positive("test", -1, result)
        assert not result.is_valid

    def test_validate_range(self):
        result = ValidationResult()
        validate_range("test", 5, 0, 3, result)
        assert not result.is_valid
