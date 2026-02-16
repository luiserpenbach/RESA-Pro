"""Tests for the engine cycle component models."""

import pytest

from resa_pro.cycle.components.base import FluidState
from resa_pro.cycle.components.pump import Pump
from resa_pro.cycle.components.turbine import Turbine
from resa_pro.cycle.components.valve import Valve
from resa_pro.cycle.components.pipe import Pipe


def _ethanol_inlet() -> FluidState:
    """Create a representative ethanol inlet state."""
    return FluidState(
        pressure=5e5,
        temperature=293.0,
        mass_flow=0.5,
        density=789.0,
        enthalpy=0.0,
        fluid_name="ethanol",
    )


def _hot_gas_inlet() -> FluidState:
    """Create a representative turbine gas inlet state."""
    return FluidState(
        pressure=20e5,
        temperature=800.0,
        mass_flow=0.1,
        density=5.0,
        enthalpy=1.2e6,
        fluid_name="combustion_gas",
    )


class TestFluidState:
    """Test FluidState dataclass."""

    def test_defaults(self):
        s = FluidState()
        assert s.pressure == 0.0
        assert s.is_two_phase is False

    def test_two_phase(self):
        s = FluidState(quality=0.5)
        assert s.is_two_phase is True

    def test_subcooled(self):
        s = FluidState(quality=-1.0)
        assert s.is_two_phase is False


class TestPump:
    """Test the pump component model."""

    def test_basic_pump(self):
        pump = Pump(name="fuel_pump", efficiency=0.65)
        inlet = _ethanol_inlet()
        outlet = pump.compute(inlet, outlet_pressure=30e5)

        assert outlet.pressure == pytest.approx(30e5)
        assert outlet.mass_flow == inlet.mass_flow
        assert outlet.temperature > inlet.temperature  # heated by inefficiency

    def test_power_positive(self):
        pump = Pump(efficiency=0.65)
        pump.compute(_ethanol_inlet(), outlet_pressure=30e5)
        assert pump.power() > 0  # consumes power

    def test_higher_dp_more_power(self):
        pump1 = Pump(efficiency=0.65)
        pump2 = Pump(efficiency=0.65)
        pump1.compute(_ethanol_inlet(), outlet_pressure=20e5)
        pump2.compute(_ethanol_inlet(), outlet_pressure=50e5)
        assert pump2.power() > pump1.power()

    def test_higher_efficiency_less_power(self):
        pump_low = Pump(efficiency=0.50)
        pump_high = Pump(efficiency=0.80)
        pump_low.compute(_ethanol_inlet(), outlet_pressure=30e5)
        pump_high.compute(_ethanol_inlet(), outlet_pressure=30e5)
        assert pump_high.power() < pump_low.power()

    def test_summary(self):
        pump = Pump(name="ox_pump")
        pump.compute(_ethanol_inlet(), outlet_pressure=30e5)
        s = pump.summary()
        assert s["name"] == "ox_pump"
        assert s["type"] == "pump"
        assert "pressure_rise_bar" in s


class TestTurbine:
    """Test the turbine component model."""

    def test_basic_turbine(self):
        turb = Turbine(name="main_turbine", efficiency=0.60)
        inlet = _hot_gas_inlet()
        outlet = turb.compute(inlet, outlet_pressure=2e5, gamma=1.3, cp=1500.0)

        assert outlet.pressure == pytest.approx(2e5)
        assert outlet.temperature < inlet.temperature  # cooled by expansion
        assert outlet.mass_flow == inlet.mass_flow

    def test_power_negative(self):
        """Turbine produces power (negative in convention)."""
        turb = Turbine(efficiency=0.60)
        turb.compute(_hot_gas_inlet(), outlet_pressure=2e5, gamma=1.3, cp=1500.0)
        assert turb.power() < 0  # produces power

    def test_higher_pr_more_power(self):
        turb1 = Turbine(efficiency=0.60)
        turb2 = Turbine(efficiency=0.60)
        turb1.compute(_hot_gas_inlet(), outlet_pressure=10e5, gamma=1.3, cp=1500.0)
        turb2.compute(_hot_gas_inlet(), outlet_pressure=1e5, gamma=1.3, cp=1500.0)
        assert abs(turb2.power()) > abs(turb1.power())

    def test_higher_efficiency_more_power(self):
        turb_low = Turbine(efficiency=0.40)
        turb_high = Turbine(efficiency=0.80)
        turb_low.compute(_hot_gas_inlet(), outlet_pressure=2e5, gamma=1.3, cp=1500.0)
        turb_high.compute(_hot_gas_inlet(), outlet_pressure=2e5, gamma=1.3, cp=1500.0)
        assert abs(turb_high.power()) > abs(turb_low.power())

    def test_summary(self):
        turb = Turbine(name="test_turb")
        turb.compute(_hot_gas_inlet(), outlet_pressure=2e5, gamma=1.3, cp=1500.0)
        s = turb.summary()
        assert "pressure_ratio" in s
        assert "shaft_power_kW" in s


class TestValve:
    """Test the valve component model."""

    def test_fixed_dp(self):
        valve = Valve(name="main_valve", dp=1e5)
        inlet = _ethanol_inlet()
        outlet = valve.compute(inlet)

        assert outlet.pressure == pytest.approx(inlet.pressure - 1e5)
        assert outlet.temperature == inlet.temperature  # isenthalpic
        assert outlet.mass_flow == inlet.mass_flow

    def test_no_power(self):
        valve = Valve(dp=1e5)
        valve.compute(_ethanol_inlet())
        assert valve.power() == 0.0

    def test_summary(self):
        valve = Valve(name="test_valve", dp=1e5)
        valve.compute(_ethanol_inlet())
        s = valve.summary()
        assert s["pressure_drop_bar"] == pytest.approx(1.0)


class TestPipe:
    """Test the pipe component model."""

    def test_basic_pipe(self):
        pipe = Pipe(name="feed_line", diameter=0.012, length=1.0)
        inlet = _ethanol_inlet()
        outlet = pipe.compute(inlet, mu=1.2e-3)

        assert outlet.pressure < inlet.pressure
        assert outlet.mass_flow == inlet.mass_flow

    def test_no_power(self):
        pipe = Pipe()
        pipe.compute(_ethanol_inlet(), mu=1.2e-3)
        assert pipe.power() == 0.0

    def test_longer_pipe_higher_dp(self):
        pipe_short = Pipe(diameter=0.012, length=0.5)
        pipe_long = Pipe(diameter=0.012, length=3.0)
        out_short = pipe_short.compute(_ethanol_inlet(), mu=1.2e-3)
        out_long = pipe_long.compute(_ethanol_inlet(), mu=1.2e-3)
        assert out_long.pressure < out_short.pressure

    def test_summary(self):
        pipe = Pipe(name="test_pipe")
        pipe.compute(_ethanol_inlet(), mu=1.2e-3)
        s = pipe.summary()
        assert "pressure_drop_bar" in s
        assert "velocity_m_s" in s
        assert "reynolds" in s


class TestPumpCp:
    """Test that pump accepts cp parameter."""

    def test_custom_cp_changes_dT(self):
        """Higher cp should give smaller temperature rise."""
        pump_low_cp = Pump(efficiency=0.65)
        pump_high_cp = Pump(efficiency=0.65)

        out_low = pump_low_cp.compute(_ethanol_inlet(), outlet_pressure=30e5, cp=1000.0)
        out_high = pump_high_cp.compute(_ethanol_inlet(), outlet_pressure=30e5, cp=4000.0)

        # Same power, but higher cp → less dT
        assert out_low.temperature > out_high.temperature

    def test_default_cp_from_density(self):
        """Without explicit cp, should estimate from density."""
        pump = Pump(efficiency=0.65)
        # liquid density > 500 → cp_est = 2000
        inlet = FluidState(pressure=5e5, temperature=300.0, mass_flow=0.5,
                           density=800.0, fluid_name="liquid")
        out = pump.compute(inlet, outlet_pressure=30e5)
        assert out.temperature > inlet.temperature


class TestTurbineDensity:
    """Test turbine outlet density uses temperature correction."""

    def test_outlet_density_accounts_for_temperature(self):
        """Outlet density should account for T_in/T_out, not just P ratio."""
        turb = Turbine(efficiency=0.60)
        inlet = _hot_gas_inlet()
        outlet = turb.compute(inlet, outlet_pressure=2e5, gamma=1.3, cp=1500.0)

        # Simple P-ratio only: rho_out = 5.0 * (2e5/20e5) = 0.5
        # With T correction: rho_out = 5.0 * (2e5/20e5) * (T_in/T_out)
        # T_out < T_in, so T_in/T_out > 1, so corrected density > 0.5
        simple_rho = inlet.density * (outlet.pressure / inlet.pressure)
        assert outlet.density > simple_rho


class TestCycleIntegration:
    """Test chaining cycle components together."""

    def test_pump_valve_pipe_chain(self):
        """Simulate: tank → pipe → valve → pump → injector."""
        tank_state = FluidState(
            pressure=25e5,
            temperature=293.0,
            mass_flow=0.5,
            density=789.0,
            fluid_name="ethanol",
        )

        pipe = Pipe(name="feed_line", diameter=0.012, length=1.5)
        valve = Valve(name="main_valve", dp=0.5e5)
        pump = Pump(name="fuel_pump", efficiency=0.65)

        state = pipe.compute(tank_state, mu=1.2e-3)
        state = valve.compute(state)
        state = pump.compute(state, outlet_pressure=30e5)

        # Final pressure should be 30 bar
        assert state.pressure == pytest.approx(30e5)
        # Mass flow preserved throughout
        assert state.mass_flow == pytest.approx(0.5)
        # Pump consumed power
        assert pump.power() > 0
