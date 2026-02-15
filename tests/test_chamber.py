"""Tests for the chamber sizing module."""

import math

import numpy as np
import pytest

from resa_pro.core.chamber import (
    ChamberGeometry,
    generate_chamber_contour,
    size_chamber_from_dimensions,
    size_chamber_from_thrust,
)
from resa_pro.utils.constants import PI


class TestChamberSizingFromThrust:
    """Test chamber sizing from thrust and Pc."""

    def test_basic_sizing(self):
        """Size a 2kN N2O/ethanol chamber at 20 bar."""
        geom = size_chamber_from_thrust(
            thrust=2000,
            chamber_pressure=2e6,
            oxidizer="n2o",
            fuel="ethanol",
            l_star=1.2,
            contraction_ratio=3.0,
        )

        # Throat diameter should be reasonable (10–50 mm for 2kN)
        assert 0.010 < geom.throat_diameter < 0.050
        # Chamber diameter > throat diameter
        assert geom.chamber_diameter > geom.throat_diameter
        # Contraction ratio should match
        assert geom.contraction_ratio == pytest.approx(3.0, rel=0.01)
        # L* should match
        assert geom.l_star == pytest.approx(1.2, rel=0.01)
        # Mass flow should be positive
        assert geom.mass_flow > 0
        # Volume = L* × At
        assert geom.chamber_volume == pytest.approx(geom.l_star * geom.throat_area, rel=0.01)

    def test_higher_thrust_larger_throat(self):
        """Higher thrust → larger throat."""
        geom_2k = size_chamber_from_thrust(2000, 2e6)
        geom_5k = size_chamber_from_thrust(5000, 2e6)
        assert geom_5k.throat_diameter > geom_2k.throat_diameter

    def test_higher_pc_smaller_throat(self):
        """Higher Pc → smaller throat (for same thrust)."""
        geom_20bar = size_chamber_from_thrust(2000, 2e6)
        geom_40bar = size_chamber_from_thrust(2000, 4e6)
        assert geom_40bar.throat_diameter < geom_20bar.throat_diameter

    def test_contour_generated(self):
        """Contour arrays should be populated."""
        geom = size_chamber_from_thrust(2000, 2e6)
        assert len(geom.contour_x) > 50
        assert len(geom.contour_x) == len(geom.contour_y)
        # First point at x=0 (injector face)
        assert geom.contour_x[0] == pytest.approx(0.0, abs=1e-6)
        # Last point radius should be near throat radius
        assert geom.contour_y[-1] == pytest.approx(geom.throat_radius, rel=0.05)
        # Contour y should start at chamber radius
        assert geom.contour_y[0] == pytest.approx(geom.chamber_radius, rel=0.01)


class TestChamberSizingFromDimensions:
    """Test chamber sizing from direct dimensions."""

    def test_from_contraction_ratio(self):
        geom = size_chamber_from_dimensions(
            throat_diameter=0.030,
            contraction_ratio=2.5,
            l_star=1.0,
        )
        expected_Dc = 0.030 * math.sqrt(2.5)
        assert geom.chamber_diameter == pytest.approx(expected_Dc, rel=1e-4)

    def test_from_chamber_diameter(self):
        geom = size_chamber_from_dimensions(
            throat_diameter=0.030,
            chamber_diameter=0.060,
        )
        expected_cr = (0.060 / 0.030) ** 2
        assert geom.contraction_ratio == pytest.approx(expected_cr, rel=1e-4)

    def test_missing_args_raises(self):
        with pytest.raises(ValueError):
            size_chamber_from_dimensions(throat_diameter=0.030)


class TestContourGeneration:
    """Test chamber contour geometry."""

    def test_contour_monotonic_decrease(self):
        """Wall radius should generally decrease from chamber to throat."""
        geom = size_chamber_from_thrust(2000, 2e6)
        # The y values should trend downward (chamber → throat)
        assert geom.contour_y[0] > geom.contour_y[-1]

    def test_contour_x_monotonic(self):
        """Axial positions should be monotonically increasing."""
        geom = size_chamber_from_thrust(2000, 2e6)
        dx = np.diff(geom.contour_x)
        assert np.all(dx >= -1e-10)  # allow tiny numerical noise
