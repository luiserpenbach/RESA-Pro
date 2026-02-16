"""Thermodynamic cycle solver for RESA Pro.

Connects cycle components (pumps, turbines, valves, pipes, heat exchangers)
into complete engine cycles and solves for power balance and system-level
performance.

Supported cycle architectures:
- Pressure-fed: tank → feed line → valve → injector (no turbopump)
- Gas-generator: separate GG drives turbine → pumps, with dumped exhaust
- Expander: nozzle/chamber heat drives turbine → pumps (closed cycle)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from scipy.optimize import brentq

from resa_pro.cycle.components.base import CycleComponent, FluidState
from resa_pro.cycle.components.heat_exchanger import HeatExchanger
from resa_pro.cycle.components.pump import Pump
from resa_pro.cycle.components.turbine import Turbine

logger = logging.getLogger(__name__)


class CycleType(Enum):
    """Engine cycle architecture."""

    PRESSURE_FED = "pressure_fed"
    GAS_GENERATOR = "gas_generator"
    EXPANDER = "expander"


@dataclass
class CyclePerformance:
    """System-level cycle performance summary."""

    cycle_type: str = ""
    chamber_pressure: float = 0.0  # Pa
    thrust: float = 0.0  # N
    total_mass_flow: float = 0.0  # kg/s
    mixture_ratio: float = 0.0  # O/F
    Isp_delivered: float = 0.0  # s — system Isp (accounting for cycle losses)
    c_star: float = 0.0  # m/s
    pump_power_total: float = 0.0  # W
    turbine_power_total: float = 0.0  # W
    power_balance_error: float = 0.0  # W — residual (should be ~0)
    tank_pressure_ox: float = 0.0  # Pa
    tank_pressure_fuel: float = 0.0  # Pa
    component_summaries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CycleDefinition:
    """Definition of a complete engine cycle.

    Contains the operating point, component list, and connectivity.
    """

    cycle_type: CycleType = CycleType.PRESSURE_FED

    # Operating point
    chamber_pressure: float = 2.0e6  # Pa
    thrust: float = 2000.0  # N
    mixture_ratio: float = 4.0  # O/F mass ratio
    c_star: float = 1550.0  # m/s
    gamma: float = 1.21
    Tc: float = 3100.0  # K — combustion chamber temperature

    # Propellant properties
    ox_density: float = 1220.0  # kg/m³
    fuel_density: float = 789.0  # kg/m³
    ox_tank_pressure: float = 25e5  # Pa (pressure-fed only)
    fuel_tank_pressure: float = 25e5  # Pa (pressure-fed only)

    # Turbopump parameters (gas-generator / expander)
    ox_pump_efficiency: float = 0.65
    fuel_pump_efficiency: float = 0.65
    turbine_efficiency: float = 0.60
    turbine_inlet_temperature: float = 800.0  # K (GG exhaust temp)
    turbine_pressure_ratio: float = 10.0
    gg_fuel_fraction: float = 0.02  # fraction of total fuel to GG
    turbine_gas_gamma: float = 1.3
    turbine_gas_cp: float = 1500.0  # J/(kg·K)

    # Feed system losses
    ox_feed_line_dp: float = 50000.0  # Pa
    fuel_feed_line_dp: float = 50000.0  # Pa
    ox_valve_dp: float = 50000.0  # Pa
    fuel_valve_dp: float = 50000.0  # Pa
    injector_dp_fraction: float = 0.15  # fraction of Pc

    # Expander cycle HX parameters
    hx_effectiveness: float = 0.80
    hx_dp_hot: float = 50000.0  # Pa — chamber-side pressure drop
    hx_dp_cold: float = 100000.0  # Pa — coolant-side pressure drop


def solve_cycle(definition: CycleDefinition) -> CyclePerformance:
    """Solve the engine cycle and compute system performance.

    Dispatches to the appropriate solver based on cycle type.

    Args:
        definition: Complete cycle definition with operating point
                    and component parameters.

    Returns:
        CyclePerformance with system-level results.

    Raises:
        ValueError: If cycle type is unknown or power balance fails.
    """
    if definition.cycle_type == CycleType.PRESSURE_FED:
        return _solve_pressure_fed(definition)
    elif definition.cycle_type == CycleType.GAS_GENERATOR:
        return _solve_gas_generator(definition)
    elif definition.cycle_type == CycleType.EXPANDER:
        return _solve_expander(definition)
    else:
        raise ValueError(f"Unknown cycle type: {definition.cycle_type}")


def _compute_flow_rates(defn: CycleDefinition) -> tuple[float, float, float]:
    """Compute mass flow rates from thrust and performance.

    Returns:
        (total_mdot, ox_mdot, fuel_mdot) in kg/s.
    """
    from resa_pro.core.thermo import (
        exit_pressure_ratio,
        thrust_coefficient,
        throat_area,
        mass_flow_rate,
    )

    # Compute thrust coefficient and throat area
    pe_pc = exit_pressure_ratio(defn.gamma, 10.0)  # assume ε=10 for sizing
    CF = thrust_coefficient(defn.gamma, 10.0, pe_pc, pa_pc=0.0)
    At = throat_area(defn.thrust, defn.chamber_pressure, CF)
    mdot_total = mass_flow_rate(defn.chamber_pressure, At, defn.c_star)

    mdot_ox = mdot_total * defn.mixture_ratio / (1.0 + defn.mixture_ratio)
    mdot_fuel = mdot_total / (1.0 + defn.mixture_ratio)

    return mdot_total, mdot_ox, mdot_fuel


# --- Pressure-fed cycle ---


def _solve_pressure_fed(defn: CycleDefinition) -> CyclePerformance:
    """Solve a pressure-fed cycle.

    Tank → Feed line → Valve → Injector → Chamber

    No turbopump; tank pressure must overcome all downstream losses.
    """
    mdot_total, mdot_ox, mdot_fuel = _compute_flow_rates(defn)
    injector_dp = defn.injector_dp_fraction * defn.chamber_pressure

    # Required tank pressures
    p_tank_ox = (
        defn.chamber_pressure
        + injector_dp
        + defn.ox_feed_line_dp
        + defn.ox_valve_dp
    )
    p_tank_fuel = (
        defn.chamber_pressure
        + injector_dp
        + defn.fuel_feed_line_dp
        + defn.fuel_valve_dp
    )

    # Trace oxidizer path
    summaries = []
    ox_state = FluidState(
        pressure=p_tank_ox,
        temperature=90.0,  # cryogenic LOX or ~ambient for N2O
        mass_flow=mdot_ox,
        density=defn.ox_density,
        fluid_name="oxidizer",
    )

    from resa_pro.cycle.components.pipe import Pipe
    from resa_pro.cycle.components.valve import Valve

    ox_pipe = Pipe(name="ox_feed_line", diameter=0.012, length=1.0)
    ox_pipe._K_minor = 0.0  # use fixed dp instead
    # Override with configured dp
    ox_state_after_pipe = FluidState(
        pressure=ox_state.pressure - defn.ox_feed_line_dp,
        temperature=ox_state.temperature,
        mass_flow=ox_state.mass_flow,
        density=ox_state.density,
        fluid_name=ox_state.fluid_name,
    )
    summaries.append({"name": "ox_feed_line", "type": "pipe", "dp_bar": defn.ox_feed_line_dp / 1e5})

    ox_valve = Valve(name="ox_valve", dp=defn.ox_valve_dp)
    ox_state_after_valve = ox_valve.compute(ox_state_after_pipe)
    summaries.append(ox_valve.summary())

    # Trace fuel path
    fuel_state = FluidState(
        pressure=p_tank_fuel,
        temperature=293.0,
        mass_flow=mdot_fuel,
        density=defn.fuel_density,
        fluid_name="fuel",
    )

    fuel_state_after_pipe = FluidState(
        pressure=fuel_state.pressure - defn.fuel_feed_line_dp,
        temperature=fuel_state.temperature,
        mass_flow=fuel_state.mass_flow,
        density=fuel_state.density,
        fluid_name=fuel_state.fluid_name,
    )
    summaries.append({"name": "fuel_feed_line", "type": "pipe", "dp_bar": defn.fuel_feed_line_dp / 1e5})

    fuel_valve = Valve(name="fuel_valve", dp=defn.fuel_valve_dp)
    fuel_state_after_valve = fuel_valve.compute(fuel_state_after_pipe)
    summaries.append(fuel_valve.summary())

    # System Isp (no cycle losses for pressure-fed)
    from resa_pro.utils.constants import G_0

    ve = defn.c_star * defn.thrust / (defn.chamber_pressure * mdot_total / defn.chamber_pressure * defn.c_star)
    # Simpler: Isp = F / (mdot * g0)
    Isp = defn.thrust / (mdot_total * G_0)

    return CyclePerformance(
        cycle_type="pressure_fed",
        chamber_pressure=defn.chamber_pressure,
        thrust=defn.thrust,
        total_mass_flow=mdot_total,
        mixture_ratio=defn.mixture_ratio,
        Isp_delivered=Isp,
        c_star=defn.c_star,
        pump_power_total=0.0,
        turbine_power_total=0.0,
        power_balance_error=0.0,
        tank_pressure_ox=p_tank_ox,
        tank_pressure_fuel=p_tank_fuel,
        component_summaries=summaries,
    )


# --- Gas-generator cycle ---


def _solve_gas_generator(defn: CycleDefinition) -> CyclePerformance:
    """Solve a gas-generator cycle.

    Oxidizer path: Tank → Pump → Feed line → Valve → Injector → Chamber
    Fuel path:     Tank → Pump → Feed line → Valve → Injector → Chamber
                                 └→ GG → Turbine → exhaust (dumped)

    The turbine power must equal the total pump power. The GG mass flow
    is iterated until power balance is achieved.
    """
    mdot_total, mdot_ox, mdot_fuel = _compute_flow_rates(defn)
    injector_dp = defn.injector_dp_fraction * defn.chamber_pressure

    # Required pump discharge pressure
    p_pump_discharge = (
        defn.chamber_pressure
        + injector_dp
        + defn.ox_feed_line_dp
        + defn.ox_valve_dp
    )

    # Tank pressures for pump-fed are much lower (just enough NPSH)
    p_tank_ox = 3e5  # ~3 bar — just for pump NPSH
    p_tank_fuel = 3e5

    # Compute pump powers
    ox_pump = Pump(name="ox_pump", efficiency=defn.ox_pump_efficiency)
    fuel_pump = Pump(name="fuel_pump", efficiency=defn.fuel_pump_efficiency)

    ox_inlet = FluidState(
        pressure=p_tank_ox,
        temperature=90.0,
        mass_flow=mdot_ox,
        density=defn.ox_density,
        fluid_name="oxidizer",
    )
    fuel_inlet = FluidState(
        pressure=p_tank_fuel,
        temperature=293.0,
        mass_flow=mdot_fuel,
        density=defn.fuel_density,
        fluid_name="fuel",
    )

    ox_pump.compute(ox_inlet, outlet_pressure=p_pump_discharge)
    fuel_pump.compute(fuel_inlet, outlet_pressure=p_pump_discharge)

    total_pump_power = ox_pump.power() + fuel_pump.power()

    # Iterate GG mass flow for power balance
    turbine = Turbine(name="gg_turbine", efficiency=defn.turbine_efficiency)
    turbine_outlet_pressure = 1e5  # exhaust to ambient

    def power_residual(gg_mdot: float) -> float:
        """Residual: turbine_power - pump_power = 0."""
        gg_inlet = FluidState(
            pressure=defn.chamber_pressure * 0.9,  # GG pressure slightly below Pc
            temperature=defn.turbine_inlet_temperature,
            mass_flow=gg_mdot,
            density=5.0,
            fluid_name="gg_exhaust",
        )
        turbine.compute(
            gg_inlet,
            outlet_pressure=turbine_outlet_pressure,
            gamma=defn.turbine_gas_gamma,
            cp=defn.turbine_gas_cp,
        )
        return abs(turbine.power()) - total_pump_power

    # Find GG mass flow that balances power
    try:
        gg_mdot_balanced = brentq(power_residual, 1e-4, mdot_total * 0.2, xtol=1e-6)
    except ValueError:
        # If root not bracketed, use simple estimate
        logger.warning("Power balance root not bracketed, using estimate")
        # W_turbine = mdot * cp * eta * T_in * (1 - (1/PR)^((g-1)/g))
        g = defn.turbine_gas_gamma
        pr = defn.turbine_pressure_ratio
        dT_ideal = defn.turbine_inlet_temperature * (1.0 - (1.0 / pr) ** ((g - 1.0) / g))
        w_specific = defn.turbine_efficiency * defn.turbine_gas_cp * dT_ideal
        gg_mdot_balanced = total_pump_power / w_specific if w_specific > 0 else 0.01

    # Final turbine computation with balanced mass flow
    gg_inlet_final = FluidState(
        pressure=defn.chamber_pressure * 0.9,
        temperature=defn.turbine_inlet_temperature,
        mass_flow=gg_mdot_balanced,
        density=5.0,
        fluid_name="gg_exhaust",
    )
    turbine.compute(
        gg_inlet_final,
        outlet_pressure=turbine_outlet_pressure,
        gamma=defn.turbine_gas_gamma,
        cp=defn.turbine_gas_cp,
    )
    turbine_power = abs(turbine.power())
    power_error = turbine_power - total_pump_power

    # System Isp penalty: GG exhaust is dumped at low Isp
    # Effective mdot for chamber = mdot_total - gg_mdot (unless reinjected)
    from resa_pro.utils.constants import G_0

    Isp_delivered = defn.thrust / (mdot_total * G_0)

    summaries = [
        ox_pump.summary(),
        fuel_pump.summary(),
        turbine.summary(),
        {"name": "gas_generator", "type": "gg", "mass_flow": gg_mdot_balanced},
    ]

    return CyclePerformance(
        cycle_type="gas_generator",
        chamber_pressure=defn.chamber_pressure,
        thrust=defn.thrust,
        total_mass_flow=mdot_total,
        mixture_ratio=defn.mixture_ratio,
        Isp_delivered=Isp_delivered,
        c_star=defn.c_star,
        pump_power_total=total_pump_power,
        turbine_power_total=turbine_power,
        power_balance_error=power_error,
        tank_pressure_ox=p_tank_ox,
        tank_pressure_fuel=p_tank_fuel,
        component_summaries=summaries,
    )


# --- Expander cycle ---


def _solve_expander(defn: CycleDefinition) -> CyclePerformance:
    """Solve an expander cycle.

    The coolant (fuel) absorbs heat from the chamber/nozzle walls,
    is expanded through a turbine to drive the pumps, then injected
    into the chamber.

    Fuel path: Tank → Pump → Cooling Jacket (HX) → Turbine → Injector → Chamber
    Ox path:   Tank → Pump → Valve → Injector → Chamber
    """
    mdot_total, mdot_ox, mdot_fuel = _compute_flow_rates(defn)
    injector_dp = defn.injector_dp_fraction * defn.chamber_pressure

    p_tank_ox = 3e5
    p_tank_fuel = 3e5

    # Pump discharge must cover chamber pressure + injector + HX + turbine inlet
    # The turbine outlet feeds the injector, so:
    # P_pump_out = P_chamber + ΔP_inj + ΔP_HX_cold + ΔP_turbine_expansion
    # We need to iterate since turbine pressure ratio affects pump power.

    ox_pump = Pump(name="ox_pump", efficiency=defn.ox_pump_efficiency)
    fuel_pump = Pump(name="fuel_pump", efficiency=defn.fuel_pump_efficiency)
    hx = HeatExchanger(
        name="regen_jacket",
        effectiveness=defn.hx_effectiveness,
        dp_hot=defn.hx_dp_hot,
        dp_cold=defn.hx_dp_cold,
    )
    turbine = Turbine(name="expander_turbine", efficiency=defn.turbine_efficiency)

    # Turbine outlet must still have enough pressure for injection
    p_turbine_outlet = defn.chamber_pressure + injector_dp

    def solve_for_pump_discharge(p_pump_out: float) -> float:
        """Residual: turbine_power - total_pump_power = 0.

        Varies the fuel pump discharge pressure until the turbine
        (driven by heated fuel) produces enough power for both pumps.
        """
        # Oxidizer pump
        ox_inlet = FluidState(
            pressure=p_tank_ox, temperature=90.0,
            mass_flow=mdot_ox, density=defn.ox_density,
            fluid_name="oxidizer",
        )
        p_ox_discharge = defn.chamber_pressure + injector_dp + defn.ox_valve_dp
        ox_pump.compute(ox_inlet, outlet_pressure=p_ox_discharge)

        # Fuel pump
        fuel_inlet = FluidState(
            pressure=p_tank_fuel, temperature=293.0,
            mass_flow=mdot_fuel, density=defn.fuel_density,
            fluid_name="fuel",
        )
        fuel_pump.compute(fuel_inlet, outlet_pressure=p_pump_out)

        total_pump = ox_pump.power() + fuel_pump.power()

        # Fuel goes through cooling jacket (HX): heated by chamber wall
        cold_in = FluidState(
            pressure=p_pump_out,
            temperature=293.0 + fuel_pump.power() / (mdot_fuel * 2500.0),
            mass_flow=mdot_fuel,
            density=defn.fuel_density,
            fluid_name="fuel",
        )
        # Hot side = chamber wall gas temperature representation
        hot_in = FluidState(
            pressure=defn.chamber_pressure,
            temperature=defn.Tc * 0.4,  # wall recovery ~40% of Tc
            mass_flow=mdot_total,  # notional
            density=5.0,
            fluid_name="hot_gas",
        )
        hx.compute(hot_in, cold_inlet=cold_in, cp_hot=1500.0, cp_cold=2500.0)
        heated_fuel = hx.cold_outlet

        if heated_fuel is None:
            return -total_pump

        # Turbine expands heated fuel
        turbine_inlet = FluidState(
            pressure=heated_fuel.pressure,
            temperature=heated_fuel.temperature,
            mass_flow=mdot_fuel,
            density=defn.fuel_density * 0.5,  # heated fuel is less dense
            enthalpy=heated_fuel.enthalpy,
            fluid_name="fuel_vapor",
        )
        turbine.compute(
            turbine_inlet,
            outlet_pressure=p_turbine_outlet,
            gamma=1.15,  # heated fuel vapor
            cp=2500.0,
        )

        return abs(turbine.power()) - total_pump

    # Search for pump discharge pressure that balances power
    # Lower bound: must exceed chamber + injector + HX losses
    p_min = defn.chamber_pressure + injector_dp + defn.hx_dp_cold + 1e5
    p_max = p_min + 50e5  # up to 50 bar above minimum

    try:
        p_balanced = brentq(solve_for_pump_discharge, p_min, p_max, xtol=1e3)
    except ValueError:
        logger.warning("Expander power balance not converged, using midpoint estimate")
        p_balanced = (p_min + p_max) / 2.0

    # Final solve at balanced pressure
    solve_for_pump_discharge(p_balanced)
    total_pump_power = ox_pump.power() + fuel_pump.power()
    turbine_power = abs(turbine.power())

    from resa_pro.utils.constants import G_0

    Isp_delivered = defn.thrust / (mdot_total * G_0)

    summaries = [
        ox_pump.summary(),
        fuel_pump.summary(),
        hx.summary(),
        turbine.summary(),
    ]

    return CyclePerformance(
        cycle_type="expander",
        chamber_pressure=defn.chamber_pressure,
        thrust=defn.thrust,
        total_mass_flow=mdot_total,
        mixture_ratio=defn.mixture_ratio,
        Isp_delivered=Isp_delivered,
        c_star=defn.c_star,
        pump_power_total=total_pump_power,
        turbine_power_total=turbine_power,
        power_balance_error=turbine_power - total_pump_power,
        tank_pressure_ox=p_tank_ox,
        tank_pressure_fuel=p_tank_fuel,
        component_summaries=summaries,
    )
