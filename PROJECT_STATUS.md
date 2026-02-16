# RESA Pro — Project Status & Development Tracker

> Last updated: 2026-02-16

## Overview

| Metric | Value |
|--------|-------|
| Source files | 73 Python modules |
| Source lines | 10,700+ LOC |
| Test files | 24 |
| Test functions | 262 (all passing) |
| Test lines | 2,867 LOC |
| CLI commands | 12 command groups |
| GUI tabs | 9 |
| Propellants | 10 |
| Materials | 7 |

---

## Phase Completion Summary

| Phase | Status | Summary |
|-------|--------|---------|
| **Phase 0** — Core Library & CLI | **Done** | Chamber, nozzle, thermo, fluids, thermal, config, CLI framework |
| **Phase 1** — Extended Analysis | **Done** | Injector, regen cooling, feed system, MOC (ideal gas), materials DB |
| **Phase 2** — Visualization & Export | **Done** | 3D STL export, HTML/text reports, PySide6 GUI (9 tabs, dark theme) |
| **Phase 3** — Optimization & Plugins | **Done** | Plugin manager, DOE, sensitivity analysis, single-objective optimizer, Monte Carlo UQ |
| **Phase 4** — Cycle Analysis | **Done** | Pressure-fed, gas-generator, expander cycle solvers with power balance |
| **Phase 5** — Hardening & Extensions | **Next** | See backlog below |

---

## Detailed Module Status

### Core Engineering (resa_pro/core/)

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Fluids | `fluids.py` | Done | CoolProp wrapper, 10 propellants, HEOS/REFPROP backend |
| Thermodynamics | `thermo.py` | Done | 14 public functions — combustion lookup (11 pairs), isentropic relations, c*/CF/Isp |
| Chamber | `chamber.py` | Done | Sizing from thrust or dimensions, ChamberGeometry, 2D contour |
| Nozzle | `nozzle.py` | Done | Conical (15°), parabolic (Rao), NozzleContour class |
| MOC | `moc.py` | Done | Prandtl-Meyer, 2D axisymmetric ideal-gas solver |
| Thermal | `thermal.py` | Done | Bartz HTC, heat flux distribution, radiative cooling, wall T estimation |
| Injector | `injector.py` | Done | Orifice sizing, element count, pressure drop, momentum ratio, chugging check |
| Cooling | `cooling.py` | Done | Rectangular channels, Dittus-Boelter/Sieder-Tate, station-by-station marching |
| Feed System | `feed_system.py` | Done | Tank sizing, blowdown/regulated pressurant, Darcy-Weisbach line losses |
| Materials | `materials.py` | Done | 7 materials, T-dependent k and Cp, JSON database |
| Config | `config.py` | Done | DesignState, JSON + HDF5 save/load, NumpyEncoder, version metadata |

### Cycle Analysis (resa_pro/cycle/)

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Cycle Solver | `solver.py` | Done | CycleDefinition, CyclePerformance, solve_cycle() dispatcher |
| Pressure-Fed | `solver.py` | Done | Direct performance calc, no turbomachinery |
| Gas-Generator | `solver.py` | Done | Brent root-finding on GG mass flow for power balance |
| Expander | `solver.py` | Done | Brent root-finding on pump discharge pressure |
| Pump | `components/pump.py` | Done | Isentropic efficiency model, PumpResult |
| Turbine | `components/turbine.py` | Done | Power extraction model, TurbineResult |
| Heat Exchanger | `components/heat_exchanger.py` | Done | Effectiveness-NTU model for expander cycles |
| Valve | `components/valve.py` | Done | Isenthalpic throttling |
| Pipe | `components/pipe.py` | Done | Friction and minor losses |

### Optimization & UQ (resa_pro/optimization/)

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Optimizer | `optimizer.py` | Done | DesignVariable, Objective, Constraint dataclasses |
| Single-Objective | `optimizer.py` | Done | Nelder-Mead, differential_evolution, L-BFGS-B via SciPy |
| DOE | `optimizer.py` | Done | Latin Hypercube Sampling |
| Sensitivity | `optimizer.py` | Done | One-at-a-time normalized sensitivity |
| UQ Engine | `uq.py` | Done | Monte Carlo propagation, 4 distribution types |
| Sensitivity Indices | `uq.py` | Done | Variance-based binning approach |
| Correlations | `uq.py` | Done | Pearson input-output correlation |

### Plugins (resa_pro/plugins/)

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Plugin Base | `base.py` | Done | Abstract Plugin class with calculate(), add_ui_tab(), add_cli_command() |
| Plugin Manager | `manager.py` | Done | PluginInfo, discover (filesystem + entry-points), enable/disable, run/run_all |
| Mass Estimator | `examples/mass_estimator.py` | Done | Example plugin using empirical T/W scaling |

### Desktop GUI (resa_pro/ui/)

| Tab / Component | File | Status | Notes |
|-----------------|------|--------|-------|
| Main Window | `main_window.py` | Done | QTabWidget, 9 tabs, menu bar, status bar, About dialog |
| App Entry | `app.py` | Done | QApplication, Fusion style, dark theme |
| Dark Theme | `styles/theme.py` | Done | Catppuccin-inspired stylesheet |
| ParamForm | `widgets/param_input.py` | Done | Reusable float/int/combo input builder |
| ResultTable | `widgets/result_display.py` | Done | 3-column QTableWidget (Param/Value/Unit) |
| LogPanel | `widgets/result_display.py` | Done | Read-only QPlainTextEdit |
| PlotCanvas | `widgets/plot_widget.py` | Done | matplotlib FigureCanvasQTAgg wrapper |
| Chamber Tab | `modules/chamber_tab.py` | Done | Size from thrust, contour plot |
| Nozzle Tab | `modules/nozzle_tab.py` | Done | Conical/parabolic design, contour visualization |
| Performance Tab | `modules/performance_tab.py` | Done | Single-point calc, expansion ratio sweep |
| Thermal Tab | `modules/thermal_tab.py` | Done | Heat flux distribution plot |
| Injector Tab | `modules/injector_tab.py` | Done | Element sizing, pressure budget bar chart |
| Cooling/Feed Tab | `modules/cooling_tab.py` | Done | Sub-tabs: regen cooling analysis + feed system |
| Cycle Tab | `modules/cycle_tab.py` | Done | 3 cycle architectures, power balance/pressure budget visualization |
| Optimize/UQ Tab | `modules/optimize_tab.py` | Done | 3 sub-tabs: optimization, DOE scatter, UQ histogram |
| Export Tab | `modules/export_tab.py` | Done | STL preview/export, propellant/material browser |

### CLI (resa_pro/cli/)

| Command | File | Status | Notes |
|---------|------|--------|-------|
| `resa chamber` | `chamber_cmd.py` | Done | Thrust or dimension input, Rich table output |
| `resa nozzle` | `nozzle_cmd.py` | Done | Conical/parabolic generation |
| `resa info` | `info_cmd.py` | Done | Subcommands: design, propellants, materials |
| `resa injector` | `injector_cmd.py` | Done | Element sizing |
| `resa cooling` | `cooling_cmd.py` | Done | Regen cooling analysis |
| `resa feed` | `feed_cmd.py` | Done | Subcommands: tank, pressurant, budget |
| `resa export-stl` | `geometry_cmd.py` | Done | STL from design JSON |
| `resa report` | `report_cmd.py` | Done | Text and HTML reports |
| `resa cycle` | `cycle_cmd.py` | Done | Cycle analysis with Rich tables |
| `resa optimize` | `optimize_cmd.py` | Done | Subcommands: isp, sensitivity, doe |
| `resa uq` | `uq_cmd.py` | Done | Monte Carlo UQ |
| `resa gui` | `gui_cmd.py` | Done | Launch PySide6 app |

### Other Modules

| Module | Files | Status | Notes |
|--------|-------|--------|-------|
| 3D Geometry | `geometry3d/engine.py` | Done | RevolutionMesh, revolve_contour(), STL binary/ASCII export |
| Reports | `reports/summary.py` | Done | generate_text_report(), generate_html_report() |
| Constants | `utils/constants.py` | Done | Physical constants, conversion factors |
| Units | `utils/units.py` | Done | Unit conversion helpers |
| Validation | `utils/validation.py` | Done | Input validation utilities |
| Interpolation | `utils/interpolation.py` | Done | linear_interp_1d and related helpers |

---

## Test Coverage

| Test File | Tests | Covers |
|-----------|-------|--------|
| `test_chamber.py` | 9 | Chamber sizing and geometry |
| `test_nozzle.py` | 13 | Conical/parabolic nozzle contours |
| `test_thermo.py` | 18 | Combustion lookup, isentropic flow, performance |
| `test_thermal.py` | 12 | Bartz HTC, heat flux, radiative cooling |
| `test_moc.py` | 9 | Method of Characteristics solver |
| `test_injector.py` | 14 | Injector element sizing |
| `test_cooling.py` | 17 | Regen cooling channels and solver |
| `test_feed_system.py` | 18 | Tank sizing, pressurant, line losses |
| `test_materials.py` | 8 | Material DB lookup and interpolation |
| `test_config.py` | 4 | JSON/HDF5 save/load |
| `test_geometry3d.py` | 12 | Revolution mesh and STL export |
| `test_reports.py` | 10 | Text and HTML report generation |
| `test_cycle.py` | 21 | Cycle components (pump, turbine, valve, pipe) |
| `test_heat_exchanger.py` | 8 | Heat exchanger component |
| `test_cycle_solver.py` | 9 | Full cycle solver (3 architectures) |
| `test_optimizer.py` | 18 | DOE, sensitivity, optimization |
| `test_uq.py` | 14 | Monte Carlo, distributions, sensitivity indices |
| `test_plugin_manager.py` | 15 | Plugin discovery, lifecycle, run |
| `test_utils.py` | 21 | Constants, units, validation, interpolation |
| `test_cli_workflow.py` | 12 | Integration: CLI end-to-end workflows |
| **Total** | **262** | |

---

## Phase 5 Backlog — Upcoming Work

The items below are organized by priority and grouped by area. They represent the next development targets based on the original project plan.

### Priority 1 — Accuracy & Validation

These items improve the physical fidelity of existing modules.

| ID | Task | Area | Effort | Notes |
|----|------|------|--------|-------|
| 5.1 | Full equilibrium chemistry (replace simplified CEA lookup table) | core/thermo | Large | Currently using 11 hard-coded propellant pair tables. Integrate NASA CEA or Cantera for real equilibrium/frozen composition calculations. |
| 5.2 | Real-gas MOC solver | core/moc | Medium | Current MOC assumes ideal gas (constant gamma). Extend to real-gas with variable gamma along characteristics. |
| 5.3 | Two-phase cooling correlations | core/cooling | Medium | Current regen solver is single-phase only. Add subcooled boiling, nucleate boiling, CHF (Kandlikar or similar). |
| 5.4 | Film cooling model | core/thermal | Medium | Add barrier cooling effectiveness model (Goldstein correlation or similar). Only a placeholder exists now. |
| 5.5 | Ablative thermal model | core/thermal | Medium | Transient ablation rate, recession tracking, char/virgin interface. |
| 5.6 | Transient thermal analysis | core/thermal | Medium | Time-stepping thermal solver for startup/shutdown transients. |
| 5.7 | Validate against known engines | tests | Medium | Cross-check outputs against published data for Merlin, Vulcain, RD-180, student engine test data. |

### Priority 2 — Extended Capabilities

New analysis modules and features.

| ID | Task | Area | Effort | Notes |
|----|------|------|--------|-------|
| 5.8 | Spiral and axial channel geometries | core/cooling | Medium | Currently only rectangular channels. Add spiral wrap and axial groove options. |
| 5.9 | Graph-based cycle solver (NetworkX) | cycle | Large | Replace current procedural solver with a graph-based fluid network. More flexible topology, enables staged combustion and full-flow cycles. |
| 5.10 | Staged combustion cycle | cycle/solver | Medium | Requires graph-based solver (5.9) or significant extension. Oxidizer-rich and fuel-rich variants. |
| 5.11 | Transient cycle simulation | cycle | Large | Time-domain startup/shutdown sequences, valve scheduling, ignition transients. |
| 5.12 | Multi-objective optimization | optimization | Medium | Pareto front (NSGA-II or similar), currently only single-objective. |
| 5.13 | Sobol sensitivity indices | optimization/uq | Small | Replace or supplement current binning-based variance decomposition with proper Sobol (Saltelli sampling). |
| 5.14 | Structural analysis (FEA integration) | new module | Large | Stress/strain on chamber wall, nozzle throat, bolt patterns. Could integrate with CalculiX or similar. |
| 5.15 | Mass budget rollup | core or new | Small | Systematic dry mass estimation from all sized components (not just plugin T/W scaling). |

### Priority 3 — Export & Documentation

Better output formats and documentation generation.

| ID | Task | Area | Effort | Notes |
|----|------|------|--------|-------|
| 5.16 | STEP export (CAD) | geometry3d | Medium | Current export is STL only. Add STEP via cadquery or OCP for parametric CAD interop. |
| 5.17 | PDF report generation | reports | Medium | Current reports are text and HTML. Add PDF via reportlab or weasyprint. |
| 5.18 | BOM generation | reports or new | Small | Bill of materials from sized components (tanks, injector elements, channels, etc.). |
| 5.19 | Manufacturing documentation | reports | Medium | Drawings, tolerances, surface finish specs from design parameters. |
| 5.20 | P&ID diagram generator | new module | Large | Piping & instrumentation diagram from cycle topology. Could use graphviz or custom SVG. |

### Priority 4 — UI & Infrastructure

User experience improvements and platform extensions.

| ID | Task | Area | Effort | Notes |
|----|------|------|--------|-------|
| 5.21 | 3D PyVista viewport in GUI | ui | Medium | Interactive 3D view of engine geometry. Currently STL preview is 2D projection only. |
| 5.22 | Streamlit web dashboard | new module | Medium | Browser-based alternative to PySide6 desktop app. |
| 5.23 | Undo/redo in GUI | ui | Small | QUndoStack for parameter changes. |
| 5.24 | Design comparison view | ui | Medium | Side-by-side comparison of two design states. |
| 5.25 | CI/CD pipeline | infra | Small | GitHub Actions for test, lint, type-check on every push. |
| 5.26 | Documentation site | infra | Medium | Sphinx or MkDocs with API reference, tutorials, theory notes. |
| 5.27 | Packaging & distribution | infra | Small | PyPI release, conda-forge recipe, Docker image. |

---

## Architecture Notes

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Numerics | NumPy, SciPy, Pandas |
| Fluid properties | CoolProp (HEOS), optional REFPROP |
| Optimization | SciPy minimize/differential_evolution |
| CLI | Click + Rich |
| Desktop GUI | PySide6 + matplotlib |
| Persistence | JSON + HDF5 (h5py) |
| Units | Pint |
| 3D geometry | Custom revolution mesh + STL export |
| Testing | pytest |

### Design Principles

1. **Modular architecture** — each analysis area is a separate module with clear API boundaries.
2. **Dataclass-heavy** — inputs and outputs use Python dataclasses for clarity and immutability.
3. **SI units internally** — all calculations in SI; conversions happen at boundaries (CLI, GUI, reports).
4. **Simplified combustion** — currently uses lookup tables rather than full equilibrium chemistry. This is the biggest physics limitation.
5. **Single-phase cooling** — regen cooling solver assumes no phase change. Two-phase correlations are a key gap.
6. **Ideal-gas MOC** — Method of Characteristics uses constant gamma. Real-gas extension needed for high-expansion-ratio nozzles.

### Known Limitations

- Combustion thermochemistry relies on pre-computed lookup tables for 11 propellant pairs, not real equilibrium calculations.
- Regen cooling solver does not handle boiling or two-phase flow.
- MOC solver assumes ideal gas (constant gamma).
- Cycle solver uses simplified component models; no transient capability.
- No structural analysis (wall stress, bolt loads, etc.).
- STL export only — no parametric CAD (STEP) output yet.
- GUI tested manually; no automated UI tests.

---

## Development Notes

### Recent Changes (Feb 2026)

1. **Phase 3+4 implementation** — Added cycle solver (3 architectures), optimization framework (DOE, sensitivity, single-objective), UQ engine (Monte Carlo, 4 distributions), plugin manager, 64 new tests.
2. **PySide6 GUI** — Built complete 9-tab desktop application with dark theme, embedded matplotlib plots, and all analysis modules accessible through the interface.
3. **Documentation** — Rewrote README.md, created this PROJECT_STATUS.md.

### Conventions

- **Branching**: Feature branches from `main`, named `claude/<description>-<id>`.
- **Testing**: Every new module gets a corresponding `test_<module>.py`. Target: every public function has at least one test.
- **Commits**: Descriptive messages, one logical change per commit.
- **Code style**: Black formatting, type hints on public APIs.

---

## Original Plan Reference

The original development plan defined five phases:

- **Phase 0**: Core library — chamber, nozzle, thermo, fluids, CLI skeleton
- **Phase 1**: Extended analysis — injector, cooling, feed system, MOC, materials
- **Phase 2**: Visualization — 3D export, reports, desktop GUI
- **Phase 3**: Intelligence — plugins, optimization, UQ
- **Phase 4**: System integration — thermodynamic cycle solver

Phases 0-4 are complete. Phase 5 (backlog above) covers hardening, accuracy improvements, and new capabilities derived from the original plan's stretch goals and identified gaps during implementation.
