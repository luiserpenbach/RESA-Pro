"""Tests for the heat exchanger cycle component."""

import pytest

from resa_pro.cycle.components.base import FluidState
from resa_pro.cycle.components.heat_exchanger import HeatExchanger


def _hot_gas() -> FluidState:
    return FluidState(
        pressure=20e5,
        temperature=1200.0,
        mass_flow=1.0,
        density=5.0,
        enthalpy=1.8e6,
        fluid_name="hot_gas",
    )


def _cold_fuel() -> FluidState:
    return FluidState(
        pressure=30e5,
        temperature=300.0,
        mass_flow=0.5,
        density=789.0,
        enthalpy=0.0,
        fluid_name="fuel",
    )


class TestHeatExchanger:
    """Test the heat exchanger component model."""

    def test_basic_heat_transfer(self):
        hx = HeatExchanger(name="regen", effectiveness=0.80, dp_hot=50000, dp_cold=100000)
        hot_in = _hot_gas()
        cold_in = _cold_fuel()

        hot_out = hx.compute(hot_in, cold_inlet=cold_in, cp_hot=1500.0, cp_cold=2500.0)

        # Hot side cooled
        assert hot_out.temperature < hot_in.temperature
        # Cold side heated
        assert hx.cold_outlet is not None
        assert hx.cold_outlet.temperature > cold_in.temperature
        # Mass flow preserved
        assert hot_out.mass_flow == hot_in.mass_flow
        assert hx.cold_outlet.mass_flow == cold_in.mass_flow

    def test_pressure_drops(self):
        dp_hot = 0.5e5
        dp_cold = 1.0e5
        hx = HeatExchanger(effectiveness=0.80, dp_hot=dp_hot, dp_cold=dp_cold)
        hot_in = _hot_gas()
        cold_in = _cold_fuel()

        hot_out = hx.compute(hot_in, cold_inlet=cold_in)

        assert hot_out.pressure == pytest.approx(hot_in.pressure - dp_hot)
        assert hx.cold_outlet.pressure == pytest.approx(cold_in.pressure - dp_cold)

    def test_effectiveness_zero(self):
        """Zero effectiveness = no heat transfer."""
        hx = HeatExchanger(effectiveness=0.0)
        hot_in = _hot_gas()
        cold_in = _cold_fuel()

        hot_out = hx.compute(hot_in, cold_inlet=cold_in)

        assert hot_out.temperature == pytest.approx(hot_in.temperature)
        assert hx.cold_outlet.temperature == pytest.approx(cold_in.temperature)

    def test_effectiveness_one(self):
        """Effectiveness 1.0 = maximum possible heat transfer."""
        hx = HeatExchanger(effectiveness=1.0, dp_hot=0, dp_cold=0)
        hot_in = _hot_gas()
        cold_in = _cold_fuel()

        hx.compute(hot_in, cold_inlet=cold_in, cp_hot=1500.0, cp_cold=2500.0)

        # C_hot = 1.0 * 1500 = 1500, C_cold = 0.5 * 2500 = 1250
        # C_min = 1250 → Q_max = 1250 * (1200 - 300) = 1125000
        # dT_cold = 1125000 / 1250 = 900
        assert hx.cold_outlet.temperature == pytest.approx(300.0 + 900.0)

    def test_no_shaft_power(self):
        hx = HeatExchanger()
        assert hx.power() == 0.0

    def test_summary(self):
        hx = HeatExchanger(name="test_hx", effectiveness=0.80)
        hx.compute(_hot_gas(), cold_inlet=_cold_fuel())
        s = hx.summary()
        assert s["name"] == "test_hx"
        assert "heat_transfer_kW" in s
        assert "effectiveness" in s

    def test_cold_outlet_before_compute(self):
        hx = HeatExchanger()
        assert hx.cold_outlet is None

    def test_higher_effectiveness_more_transfer(self):
        hx_low = HeatExchanger(effectiveness=0.3, dp_hot=0, dp_cold=0)
        hx_high = HeatExchanger(effectiveness=0.9, dp_hot=0, dp_cold=0)

        hx_low.compute(_hot_gas(), cold_inlet=_cold_fuel())
        hx_high.compute(_hot_gas(), cold_inlet=_cold_fuel())

        assert hx_high.cold_outlet.temperature > hx_low.cold_outlet.temperature
