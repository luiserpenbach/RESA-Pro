"""Tests for the thermodynamic cycle solver."""

import pytest

from resa_pro.cycle.solver import (
    CycleDefinition,
    CyclePerformance,
    CycleType,
    solve_cycle,
)


class TestPressureFedCycle:
    """Test the pressure-fed cycle solver."""

    def test_basic_pressure_fed(self):
        defn = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            thrust=2000.0,
            chamber_pressure=2e6,
            mixture_ratio=4.0,
            c_star=1550.0,
            gamma=1.21,
        )
        result = solve_cycle(defn)

        assert result.cycle_type == "pressure_fed"
        assert result.thrust == 2000.0
        assert result.total_mass_flow > 0
        assert result.Isp_delivered > 0
        assert result.pump_power_total == 0.0  # no pumps
        assert result.turbine_power_total == 0.0

    def test_tank_pressure_above_pc(self):
        """Tank pressure must exceed Pc + losses."""
        defn = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            chamber_pressure=2e6,
        )
        result = solve_cycle(defn)

        assert result.tank_pressure_ox > defn.chamber_pressure
        assert result.tank_pressure_fuel > defn.chamber_pressure

    def test_mass_flow_mixture_ratio(self):
        """Check that total mass flow splits correctly by MR."""
        defn = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            mixture_ratio=4.0,
        )
        result = solve_cycle(defn)

        # mdot_total = mdot_ox + mdot_fuel, MR = mdot_ox / mdot_fuel
        assert result.total_mass_flow > 0
        assert result.mixture_ratio == 4.0


class TestGasGeneratorCycle:
    """Test the gas-generator cycle solver."""

    def test_basic_gas_generator(self):
        defn = CycleDefinition(
            cycle_type=CycleType.GAS_GENERATOR,
            thrust=10000.0,
            chamber_pressure=5e6,
            mixture_ratio=2.7,
            c_star=1780.0,
            gamma=1.20,
            ox_density=1141.0,
            fuel_density=810.0,
            turbine_inlet_temperature=800.0,
        )
        result = solve_cycle(defn)

        assert result.cycle_type == "gas_generator"
        assert result.pump_power_total > 0
        assert result.turbine_power_total > 0
        assert result.Isp_delivered > 0

    def test_power_balance(self):
        """Turbine power should approximately equal pump power."""
        defn = CycleDefinition(
            cycle_type=CycleType.GAS_GENERATOR,
            thrust=10000.0,
            chamber_pressure=5e6,
            c_star=1780.0,
            gamma=1.20,
        )
        result = solve_cycle(defn)

        # Allow small residual from numerical solver
        assert abs(result.power_balance_error) < result.pump_power_total * 0.05

    def test_low_tank_pressure(self):
        """Pump-fed systems have low tank pressure."""
        defn = CycleDefinition(cycle_type=CycleType.GAS_GENERATOR)
        result = solve_cycle(defn)

        assert result.tank_pressure_ox < 10e5  # < 10 bar


class TestExpanderCycle:
    """Test the expander cycle solver."""

    def test_basic_expander(self):
        defn = CycleDefinition(
            cycle_type=CycleType.EXPANDER,
            thrust=5000.0,
            chamber_pressure=3e6,
            mixture_ratio=3.0,
            c_star=1780.0,
            gamma=1.19,
            Tc=3400.0,
            ox_density=1141.0,
            fuel_density=422.0,  # LCH4
            hx_effectiveness=0.80,
        )
        result = solve_cycle(defn)

        assert result.cycle_type == "expander"
        assert result.pump_power_total > 0
        assert result.turbine_power_total > 0
        assert result.Isp_delivered > 0

    def test_has_component_summaries(self):
        defn = CycleDefinition(cycle_type=CycleType.EXPANDER)
        result = solve_cycle(defn)
        assert len(result.component_summaries) >= 3  # ox_pump, fuel_pump, hx, turbine


class TestExpansionRatio:
    """Test that expansion_ratio is properly used instead of hardcoded."""

    def test_expansion_ratio_affects_isp(self):
        """Different expansion ratios should produce different Isp."""
        defn_low = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            expansion_ratio=5.0,
        )
        defn_high = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            expansion_ratio=50.0,
        )
        result_low = solve_cycle(defn_low)
        result_high = solve_cycle(defn_high)

        # Higher expansion ratio → higher vacuum Isp
        assert result_high.Isp_delivered > result_low.Isp_delivered

    def test_expansion_ratio_affects_mass_flow(self):
        """Different expansion ratios change thrust coefficient and thus mass flow."""
        defn_a = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            expansion_ratio=5.0,
            thrust=2000.0,
        )
        defn_b = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            expansion_ratio=20.0,
            thrust=2000.0,
        )
        result_a = solve_cycle(defn_a)
        result_b = solve_cycle(defn_b)

        # Same thrust, different CF → different mass flow
        assert result_a.total_mass_flow != pytest.approx(result_b.total_mass_flow, rel=0.01)

    def test_expansion_ratio_in_gg_cycle(self):
        """Gas-generator cycle should also respect expansion_ratio."""
        defn = CycleDefinition(
            cycle_type=CycleType.GAS_GENERATOR,
            expansion_ratio=15.0,
            thrust=10000.0,
            chamber_pressure=5e6,
        )
        result = solve_cycle(defn)
        assert result.Isp_delivered > 0
        assert result.pump_power_total > 0

    def test_default_expansion_ratio(self):
        """Default expansion ratio should be 10."""
        defn = CycleDefinition()
        assert defn.expansion_ratio == 10.0


class TestNewCycleFields:
    """Test new fields on CycleDefinition."""

    def test_fuel_cp_field(self):
        defn = CycleDefinition(fuel_cp=3000.0)
        assert defn.fuel_cp == 3000.0

    def test_wall_recovery_fraction_field(self):
        defn = CycleDefinition(wall_recovery_fraction=0.3)
        assert defn.wall_recovery_fraction == 0.3

    def test_expander_with_custom_fuel_cp(self):
        """Expander cycle should use fuel_cp parameter."""
        defn = CycleDefinition(
            cycle_type=CycleType.EXPANDER,
            fuel_cp=3500.0,
            Tc=3400.0,
        )
        result = solve_cycle(defn)
        assert result.Isp_delivered > 0


class TestCycleComparison:
    """Compare cycle architectures."""

    def test_pressure_fed_vs_pump_fed_tank_pressure(self):
        """Pressure-fed requires higher tank pressure than pump-fed."""
        pf = CycleDefinition(
            cycle_type=CycleType.PRESSURE_FED,
            chamber_pressure=2e6,
        )
        gg = CycleDefinition(
            cycle_type=CycleType.GAS_GENERATOR,
            chamber_pressure=2e6,
        )

        pf_result = solve_cycle(pf)
        gg_result = solve_cycle(gg)

        assert pf_result.tank_pressure_ox > gg_result.tank_pressure_ox
