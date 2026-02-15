# RESA Pro — Rocket Engine Sizing and Analysis

A comprehensive, modular rocket engine design and analysis tool built on Python with real gas properties via CoolProp.

RESA Pro provides advanced capabilities for chamber sizing, nozzle contour generation, thermal analysis, and more — packaged as both a Python library and a command-line tool.

## Features

- **Chamber Sizing** — from thrust/Pc requirements or direct dimensions
- **Nozzle Contour Generation** — conical, parabolic (Rao), and Method of Characteristics
- **Thermal Analysis** — Bartz heat transfer, heat flux distribution, radiative cooling, wall temperature estimation
- **Real Gas Properties** — CoolProp integration with 10 propellants (ethanol, N2O, LOX, RP-1, methane, hydrogen, etc.)
- **Material Database** — temperature-dependent properties for copper alloys, stainless steel, Inconel, aluminum, and ablatives
- **Design Persistence** — JSON + HDF5 save/load with version metadata
- **CLI Interface** — Rich-formatted terminal output for quick sizing and analysis

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/RESA-Pro.git
cd RESA-Pro

# Install in development mode
pip install -e ".[dev]"
```

### Dependencies

Core: Python 3.10+, NumPy, SciPy, CoolProp, Click, Rich, h5py, Pint

Optional extras:
```bash
pip install -e ".[cad]"      # CAD export (cadquery, trimesh)
pip install -e ".[ui]"       # Desktop GUI (PySide6, PyVista)
pip install -e ".[reports]"  # Report generation (reportlab, Plotly)
pip install -e ".[all]"      # Everything
```

## Quick Start

### CLI

```bash
# Size a combustion chamber for a 2 kN N2O/ethanol engine at 20 bar
resa chamber --thrust 2000 --pc 2000000 --oxidizer n2o --fuel ethanol

# Design a parabolic nozzle with expansion ratio 10
resa chamber --thrust 2000 --pc 2000000 -o chamber.json
resa nozzle --expansion-ratio 10 --method parabolic --design chamber.json

# List available propellants and materials
resa info propellants
resa info materials

# Inspect a saved design
resa info design chamber.json
```

### Python API

```python
from resa_pro.core.chamber import size_chamber_from_thrust
from resa_pro.core.nozzle import parabolic_nozzle
from resa_pro.core.thermo import compute_nozzle_performance, lookup_combustion
from resa_pro.core.thermal import compute_heat_flux_distribution

# Size a chamber
geom = size_chamber_from_thrust(
    thrust=2000,           # N
    chamber_pressure=2e6,  # Pa
    oxidizer="n2o",
    fuel="ethanol",
    l_star=1.2,            # m
    contraction_ratio=3.0,
)
print(f"Throat diameter: {geom.throat_diameter * 1e3:.1f} mm")
print(f"Chamber diameter: {geom.chamber_diameter * 1e3:.1f} mm")

# Generate a nozzle contour
nozzle = parabolic_nozzle(
    throat_radius=geom.throat_radius,
    expansion_ratio=10,
    fractional_length=0.8,
)
print(f"Nozzle length: {nozzle.length * 1e3:.1f} mm")
print(f"Divergence efficiency: {nozzle.divergence_efficiency:.4f}")

# Compute performance
comb = lookup_combustion("n2o", "ethanol", mixture_ratio=4.0)
perf = compute_nozzle_performance(
    gamma=comb.gamma,
    molar_mass=comb.molar_mass,
    Tc=comb.chamber_temperature,
    expansion_ratio=10,
    pc=2e6,
)
print(f"Isp (vacuum): {perf.Isp_vac:.1f} s")
print(f"c*: {perf.c_star:.0f} m/s")

# Heat flux distribution along the chamber wall
results = compute_heat_flux_distribution(
    contour_x=geom.contour_x,
    contour_y=geom.contour_y,
    throat_radius=geom.throat_radius,
    pc=2e6, c_star=perf.c_star,
    Tc=comb.chamber_temperature,
    gamma=comb.gamma,
    molar_mass=comb.molar_mass,
)
peak_q = max(r.q_dot for r in results)
print(f"Peak heat flux: {peak_q / 1e6:.1f} MW/m²")
```

## Project Structure

```
RESA-Pro/
├── resa_pro/
│   ├── core/              # Core calculation modules
│   │   ├── fluids.py      # CoolProp wrapper, propellant database
│   │   ├── thermo.py      # Combustion, isentropic flow, c*/CF/Isp
│   │   ├── chamber.py     # Chamber sizing and contour generation
│   │   ├── nozzle.py      # Conical and parabolic nozzle contours
│   │   ├── moc.py         # Method of Characteristics solver
│   │   ├── thermal.py     # Bartz equation, heat flux, radiation
│   │   ├── materials.py   # Material property database
│   │   └── config.py      # Design state management (JSON + HDF5)
│   ├── cli/               # Click-based CLI commands
│   ├── plugins/           # Plugin base class and examples
│   ├── utils/             # Constants, units, validation, interpolation
│   ├── geometry3d/        # 3D geometry generation (planned)
│   ├── cycle/             # Thermodynamic cycle solver (planned)
│   ├── ui/                # PySide6 desktop application (planned)
│   └── reports/           # Report generation (planned)
├── data/
│   ├── propellants.json   # 10 propellants with CoolProp mappings
│   └── materials.json     # 7 materials with T-dependent properties
└── tests/                 # 94 unit tests
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
pytest tests/ -v
```

## Roadmap

- **Phase 0** (current) — Core library, CLI, basic analysis
- **Phase 1** — Advanced nozzle (real-gas MOC), regenerative cooling (two-phase), feed system sizing
- **Phase 2** — PySide6 desktop application with 3D visualization
- **Phase 3** — Plugin system, optimization framework, uncertainty quantification
- **Phase 4** — Thermodynamic cycle solver (modular component-based simulation)

## License

MIT
