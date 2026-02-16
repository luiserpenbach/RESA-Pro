"""Tests for the report generation module."""

import pytest

from resa_pro.core.config import DesignState, ProjectMeta
from resa_pro.reports.summary import generate_html_report, generate_text_report


def _make_state() -> DesignState:
    """Create a sample DesignState for testing."""
    return DesignState(
        meta=ProjectMeta(name="Test Engine"),
        oxidizer="n2o",
        fuel="ethanol",
        mixture_ratio=4.0,
        chamber_pressure=2e6,
        thrust=2000.0,
        chamber={
            "throat_diameter": 0.025,
            "chamber_diameter": 0.060,
            "chamber_length": 0.100,
            "contraction_ratio": 3.0,
            "l_star": 1.2,
            "chamber_volume": 5e-5,
            "mass_flow": 1.2,
        },
        nozzle={
            "method": "parabolic",
            "expansion_ratio": 10.0,
            "exit_radius": 0.04,
            "length": 0.08,
            "divergence_efficiency": 0.985,
        },
        performance={
            "c_star": 1550.0,
            "CF_vac": 1.75,
            "CF_sl": 1.40,
            "Isp_vac": 276.0,
            "Isp_sl": 221.0,
            "exit_mach": 3.2,
        },
        feed_system={
            "injector": {
                "mass_flow_oxidizer": 0.96,
                "mass_flow_fuel": 0.24,
                "dp_oxidizer": 4e5,
                "dp_fuel": 4e5,
                "n_elements_ox": 12,
                "element_diameter_ox": 1.5e-3,
                "n_elements_fuel": 12,
                "element_diameter_fuel": 1.2e-3,
                "momentum_ratio": 1.8,
            },
        },
        cooling={
            "coolant": "ethanol",
            "wall_material": "copper",
            "coolant_mass_flow": 0.24,
            "coolant_outlet_temp": 340.0,
            "max_wall_temperature": 650.0,
            "max_heat_flux": 8e6,
            "total_heat_load": 50e3,
            "total_pressure_drop": 3e5,
        },
    )


class TestTextReport:
    """Test plain-text report generation."""

    def test_generates_string(self):
        report = generate_text_report(_make_state())
        assert isinstance(report, str)
        assert len(report) > 100

    def test_contains_key_sections(self):
        report = generate_text_report(_make_state())
        assert "OPERATING POINT" in report
        assert "CHAMBER GEOMETRY" in report
        assert "NOZZLE DESIGN" in report
        assert "PERFORMANCE" in report
        assert "INJECTOR DESIGN" in report
        assert "REGENERATIVE COOLING" in report

    def test_contains_values(self):
        report = generate_text_report(_make_state())
        assert "n2o" in report
        assert "ethanol" in report
        assert "2000" in report  # thrust
        assert "1550" in report  # c_star

    def test_empty_state_still_works(self):
        report = generate_text_report(DesignState())
        assert "OPERATING POINT" in report
        # Should not crash on empty dicts

    def test_contains_footer(self):
        report = generate_text_report(_make_state())
        assert "RESA Pro" in report


class TestHtmlReport:
    """Test HTML report generation."""

    def test_generates_html(self):
        report = generate_html_report(_make_state())
        assert report.startswith("<!DOCTYPE html>")
        assert "</html>" in report

    def test_contains_tables(self):
        report = generate_html_report(_make_state())
        assert "<table>" in report
        assert "Operating Point" in report
        assert "Chamber Geometry" in report

    def test_contains_values(self):
        report = generate_html_report(_make_state())
        assert "n2o" in report
        assert "ethanol" in report

    def test_valid_structure(self):
        report = generate_html_report(_make_state())
        assert "<head>" in report
        assert "<body>" in report
        assert "</body>" in report
        assert report.count("<table>") == report.count("</table>")

    def test_empty_state(self):
        report = generate_html_report(DesignState())
        assert "</html>" in report


class TestReportCycleSection:
    """Test that cycle analysis data appears in reports."""

    def _state_with_cycle(self) -> DesignState:
        state = _make_state()
        state.performance["cycle"] = {
            "cycle_type": "gas_generator",
            "Isp_delivered": 285.0,
            "total_mass_flow": 3.5,
            "pump_power_total": 45000.0,
            "turbine_power_total": 45200.0,
            "power_balance_error": 200.0,
            "tank_pressure_ox": 3e5,
            "tank_pressure_fuel": 3e5,
        }
        return state

    def test_text_report_cycle_section(self):
        report = generate_text_report(self._state_with_cycle())
        assert "CYCLE ANALYSIS" in report
        assert "Gas Generator" in report
        assert "285" in report  # Isp

    def test_html_report_cycle_section(self):
        report = generate_html_report(self._state_with_cycle())
        assert "Cycle Analysis" in report
        assert "Gas Generator" in report


class TestReportOptimizationSection:
    """Test that optimization data appears in reports."""

    def _state_with_opt(self) -> DesignState:
        state = _make_state()
        state.performance["optimization"] = {
            "method": "differential_evolution",
            "n_evaluations": 150,
            "best_variables": {"chamber_pressure": 3.5e6, "expansion_ratio": 12.0},
            "best_objectives": {"Isp_vac": 290.5},
        }
        return state

    def test_text_report_optimization_section(self):
        report = generate_text_report(self._state_with_opt())
        assert "OPTIMIZATION RESULTS" in report
        assert "differential_evolution" in report

    def test_html_report_optimization_section(self):
        report = generate_html_report(self._state_with_opt())
        assert "Optimization Results" in report
        assert "differential_evolution" in report
