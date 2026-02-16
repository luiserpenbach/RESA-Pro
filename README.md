# RESA Pro — Rocket Engine Sizing and Analysis

A comprehensive, modular rocket engine design and analysis tool built on Python with real gas properties via CoolProp. Developed by Space Team Aachen.

RESA Pro provides chamber sizing, nozzle contour generation, thermal analysis, regenerative cooling, feed system sizing, thermodynamic cycle analysis, design optimization, and uncertainty quantification — packaged as a Python library, CLI tool, and PySide6 desktop application.

**10,700+ lines of source** | **262 tests** | **12 CLI commands** | **9-tab desktop GUI**

## Features

### Core Analysis
- **Chamber Sizing** — from thrust/Pc requirements or direct dimensions, with 2D contour generation
- **Nozzle Design** — conical (15° standard), parabolic (Rao thrust-optimized), and Method of Characteristics (ideal gas)
- **Performance Analysis** — combustion lookup (11 propellant pairs), isentropic flow relations, c\*/CF/Isp
- **Thermal Analysis** — Bartz convective heat transfer, heat flux distribution, radiative cooling equilibrium, 1-D wall thermal resistance
- **Injector Design** — orifice sizing, element count, pressure drop, momentum ratio, chugging stability check
- **Regenerative Cooling** — rectangular channel geometry, Dittus-Boelter/Sieder-Tate HTCs, station-by-station marching solver
- **Feed System** — tank sizing (thin-wall pressure vessel), blowdown/regulated pressurant, feed line losses, pressure budget

### System-Level Analysis
- **Thermodynamic Cycle Solver** — pressure-fed, gas-generator, and expander cycles with iterative power balance (Brent root-finding)
- **Optimization Framework** — design space definition, Latin Hypercube DOE, one-at-a-time sensitivity analysis, single-objective optimization (Nelder-Mead, differential evolution, L-BFGS-B)
- **Uncertainty Quantification** — Monte Carlo propagation (normal, uniform, triangular, lognormal), variance-based sensitivity indices, input-output correlation analysis

### Infrastructure
- **Real Gas Properties** — CoolProp integration with 10 propellants and optional REFPROP backend
- **Material Database** — 7 materials with temperature-dependent thermal conductivity and specific heat
- **Design Persistence** — JSON + HDF5 save/load with numpy array support and version metadata
- **3D Geometry** — revolution body mesh generation from 2D contours, binary/ASCII STL export
- **Plugin System** — plugin manager with filesystem and entry-point discovery, enable/disable, run-all
- **Report Generation** — plain-text and HTML design summaries
- **CLI** — 12 Rich-formatted command groups (chamber, nozzle, info, injector, cooling, feed, export-stl, report, cycle, optimize, uq, gui)
- **Desktop GUI** — PySide6 application with 9 analysis tabs, dark theme, embedded matplotlib plots

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/RESA-Pro.git
cd RESA-Pro

# Install in development mode
pip install -e ".[dev]"
```

### Dependencies

Core: Python 3.10+, NumPy, SciPy, Pandas, CoolProp, Click, Rich, h5py, Pint

Optional extras:
```bash
pip install -e ".[ui]"       # Desktop GUI (PySide6, matplotlib)
pip install -e ".[cad]"      # CAD export (cadquery, trimesh)
pip install -e ".[reports]"  # Report generation (reportlab, Plotly, Jinja2)
pip install -e ".[all]"      # Everything
```

## Quick Start

### Desktop GUI

```bash
resa gui
# or
python -m resa_pro.ui.app
```

### CLI

```bash
# Size a combustion chamber for a 2 kN N2O/ethanol engine at 20 bar
resa chamber --thrust 2000 --pc 2000000 --oxidizer n2o --fuel ethanol

# Design a parabolic nozzle with expansion ratio 10
resa nozzle --expansion-ratio 10 --method parabolic --design chamber.json

# Analyze a gas-generator cycle
resa cycle analyze --type gas-generator --thrust 10000 --pc 5e6

# Optimize Isp over expansion ratio and chamber pressure
resa optimize isp --oxidizer n2o --fuel ethanol --method differential_evolution

# Run Monte Carlo uncertainty propagation
resa uq monte-carlo --pc 2e6 --pc-std 0.1e6 --samples 1000

# Run Latin Hypercube DOE
resa optimize doe --samples 50 --output doe_results.json

# Export 3D STL geometry
resa export-stl --design engine.json -o engine.stl

# List available propellants and materials
resa info propellants
resa info materials
```

### Python API

```python
from resa_pro.core.chamber import size_chamber_from_thrust
from resa_pro.core.nozzle import parabolic_nozzle
from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion

# Size a chamber
geom = size_chamber_from_thrust(
    thrust=2000, chamber_pressure=2e6,
    oxidizer="n2o", fuel="ethanol",
    l_star=1.2, contraction_ratio=3.0,
)

# Design a nozzle
nozzle = parabolic_nozzle(throat_radius=geom.throat_radius, expansion_ratio=10)

# Compute performance
comb = lookup_combustion("n2o", "ethanol", mixture_ratio=4.0)
perf = compute_nozzle_performance(
    gamma=comb.gamma, molar_mass=comb.molar_mass,
    Tc=comb.chamber_temperature, expansion_ratio=10, pc=2e6,
)
print(f"Isp (vacuum): {perf.Isp_vac:.1f} s")
print(f"c*: {perf.c_star:.0f} m/s")
```

```python
# Cycle analysis
from resa_pro.cycle.solver import CycleDefinition, CycleType, solve_cycle

defn = CycleDefinition(
    cycle_type=CycleType.GAS_GENERATOR,
    thrust=10000, chamber_pressure=5e6,
    mixture_ratio=2.7, c_star=1780,
)
result = solve_cycle(defn)
print(f"Isp: {result.Isp_delivered:.1f} s, Pump power: {result.pump_power_total/1e3:.1f} kW")
```

```python
# Optimization
from resa_pro.optimization.optimizer import DesignOptimizer, DesignVariable, Objective

opt = DesignOptimizer()
opt.add_variable(DesignVariable("chamber_pressure", 1e6, 5e6, unit="Pa"))
opt.add_variable(DesignVariable("expansion_ratio", 3.0, 50.0))
opt.add_objective(Objective("Isp_vac", "Isp_vac", direction="maximize"))
result = opt.optimize(eval_func, method="differential_evolution")
```

## Project Structure

```
RESA-Pro/
├── resa_pro/
│   ├── core/                # Core calculation modules (12 files)
│   │   ├── fluids.py        # CoolProp wrapper, propellant database
│   │   ├── thermo.py        # Combustion lookup, isentropic flow, c*/CF/Isp
│   │   ├── chamber.py       # Chamber sizing and contour generation
│   │   ├── nozzle.py        # Conical, parabolic nozzle contours + efficiency
│   │   ├── moc.py           # Method of Characteristics solver (ideal gas)
│   │   ├── thermal.py       # Bartz equation, heat flux, radiative cooling
│   │   ├── injector.py      # Injector element sizing and spray analysis
│   │   ├── cooling.py       # Regenerative cooling (rectangular channels)
│   │   ├── feed_system.py   # Tanks, pressurant, pressure budget, feed lines
│   │   ├── materials.py     # Material property database (T-dependent)
│   │   └── config.py        # Design state management (JSON + HDF5)
│   ├── cycle/               # Thermodynamic cycle analysis
│   │   ├── components/      # Pump, turbine, valve, pipe, heat exchanger
│   │   └── solver.py        # Pressure-fed, gas-generator, expander solver
│   ├── optimization/        # Design optimization and UQ
│   │   ├── optimizer.py     # DOE, sensitivity, single-objective optimization
│   │   └── uq.py            # Monte Carlo, distributions, sensitivity indices
│   ├── geometry3d/          # 3D mesh generation and STL export
│   ├── reports/             # Text and HTML report generation
│   ├── plugins/             # Plugin system with manager and examples
│   ├── cli/                 # 12 Click-based CLI command groups
│   ├── ui/                  # PySide6 desktop application
│   │   ├── main_window.py   # Main window with 9-tab interface
│   │   ├── modules/         # Tab modules (chamber, nozzle, performance, ...)
│   │   ├── widgets/         # ParamForm, ResultTable, PlotCanvas, LogPanel
│   │   └── styles/          # Dark theme stylesheet
│   └── utils/               # Constants, units, validation, interpolation
├── data/
│   ├── propellants.json     # 10 propellants with CoolProp mappings
│   └── materials.json       # 7 materials with T-dependent properties
└── tests/                   # 262 tests across 20 test modules
```

## Available Propellants

| Name | Formula | Type | CoolProp Backend |
|------|---------|------|-----------------|
| ethanol | C2H5OH | fuel | Ethanol |
| n2o | N2O | oxidizer | NitrousOxide |
| lox | O2 | oxidizer | Oxygen |
| rp1 | C12H26 | fuel | n-Dodecane |
| methane | CH4 | fuel | Methane |
| hydrogen | H2 | fuel | Hydrogen |
| nitrogen | N2 | pressurant | Nitrogen |
| helium | He | pressurant | Helium |
| water | H2O | coolant | Water |
| isopropanol | C3H7OH | fuel | Isopropanol |

## Available Materials

| ID | Name | Category | Density (kg/m³) |
|----|------|----------|----------------|
| copper_c10100 | C10100 OFE Copper | copper alloy | 8941 |
| copper_c18150 | C18150 CuCrZr | copper alloy | 8890 |
| ss316 | 316 Stainless Steel | stainless steel | 7990 |
| inconel_718 | Inconel 718 | nickel alloy | 8190 |
| al6061_t6 | 6061-T6 Aluminum | aluminum alloy | 2700 |
| graphite | Graphite (ATJ grade) | ablative | 1780 |
| silica_phenolic | Silica Phenolic | ablative | 1720 |

## Running Tests

```bash
pytest tests/ -v              # full suite (262 tests)
pytest tests/ -v --tb=short   # compact output
pytest tests/test_chamber.py  # single module
```

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 0** | Done | Core library, CLI, basic analysis |
| **Phase 1** | Done | Injector design, regen cooling, feed system, MOC (ideal gas) |
| **Phase 2** | Done | 3D STL export, HTML/text reports, PySide6 desktop GUI (9 tabs) |
| **Phase 3** | Done | Plugin manager, optimization framework (DOE, sensitivity, optimizer), UQ (Monte Carlo) |
| **Phase 4** | Done | Thermodynamic cycle solver (pressure-fed, gas-generator, expander) |
| **Phase 5** | Next | See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed backlog and next steps |

## License

MIT
