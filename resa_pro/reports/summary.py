"""Design summary report generation for RESA Pro.

Produces text and HTML reports from a DesignState, summarising chamber,
nozzle, injector, cooling, feed system, and performance data.
"""

from __future__ import annotations

import html as html_mod
from datetime import datetime, timezone
from typing import Any

from resa_pro.core.config import DesignState


# --- Plain-text report ---


def generate_text_report(state: DesignState) -> str:
    """Generate a plain-text design summary report.

    Args:
        state: DesignState with design data.

    Returns:
        Multi-line text report string.
    """
    lines: list[str] = []
    _hr = "=" * 60

    lines.append(_hr)
    lines.append(f"  RESA Pro — Design Report")
    lines.append(f"  {state.meta.name}")
    lines.append(_hr)
    lines.append("")

    # Operating point
    lines.append("OPERATING POINT")
    lines.append("-" * 40)
    lines.append(f"  Oxidizer:          {state.oxidizer}")
    lines.append(f"  Fuel:              {state.fuel}")
    lines.append(f"  Mixture Ratio:     {state.mixture_ratio:.2f}")
    lines.append(f"  Chamber Pressure:  {state.chamber_pressure / 1e5:.1f} bar")
    lines.append(f"  Thrust:            {state.thrust:.0f} N")
    lines.append("")

    # Chamber
    if state.chamber:
        lines.append("CHAMBER GEOMETRY")
        lines.append("-" * 40)
        _add_param(lines, "Throat Diameter", state.chamber, "throat_diameter", "mm", 1e3)
        _add_param(lines, "Chamber Diameter", state.chamber, "chamber_diameter", "mm", 1e3)
        _add_param(lines, "Chamber Length", state.chamber, "chamber_length", "mm", 1e3)
        _add_param(lines, "Contraction Ratio", state.chamber, "contraction_ratio")
        _add_param(lines, "L*", state.chamber, "l_star", "m")
        _add_param(lines, "Chamber Volume", state.chamber, "chamber_volume", "cm³", 1e6)
        _add_param(lines, "Mass Flow Rate", state.chamber, "mass_flow", "kg/s")
        lines.append("")

    # Nozzle
    if state.nozzle:
        lines.append("NOZZLE DESIGN")
        lines.append("-" * 40)
        _add_param_str(lines, "Method", state.nozzle.get("method", "—"))
        _add_param(lines, "Expansion Ratio", state.nozzle, "expansion_ratio")
        _add_param(lines, "Exit Radius", state.nozzle, "exit_radius", "mm", 1e3)
        _add_param(lines, "Nozzle Length", state.nozzle, "length", "mm", 1e3)
        _add_param(lines, "Div. Efficiency", state.nozzle, "divergence_efficiency")
        lines.append("")

    # Performance
    if state.performance:
        lines.append("PERFORMANCE")
        lines.append("-" * 40)
        _add_param(lines, "c*", state.performance, "c_star", "m/s")
        _add_param(lines, "CF (vacuum)", state.performance, "CF_vac")
        _add_param(lines, "CF (sea level)", state.performance, "CF_sl")
        _add_param(lines, "Isp (vacuum)", state.performance, "Isp_vac", "s")
        _add_param(lines, "Isp (sea level)", state.performance, "Isp_sl", "s")
        _add_param(lines, "Exit Mach", state.performance, "exit_mach")
        lines.append("")

    # Injector
    inj = state.feed_system.get("injector")
    if inj:
        lines.append("INJECTOR DESIGN")
        lines.append("-" * 40)
        _add_param(lines, "Oxidizer Flow", inj, "mass_flow_oxidizer", "kg/s")
        _add_param(lines, "Fuel Flow", inj, "mass_flow_fuel", "kg/s")
        _add_param(lines, "ΔP Oxidizer", inj, "dp_oxidizer", "bar", 1e-5)
        _add_param(lines, "ΔP Fuel", inj, "dp_fuel", "bar", 1e-5)
        _add_param(lines, "Elements (ox)", inj, "n_elements_ox")
        _add_param(lines, "Orifice Ø (ox)", inj, "element_diameter_ox", "mm", 1e3)
        _add_param(lines, "Elements (fuel)", inj, "n_elements_fuel")
        _add_param(lines, "Orifice Ø (fuel)", inj, "element_diameter_fuel", "mm", 1e3)
        _add_param(lines, "Momentum Ratio", inj, "momentum_ratio")
        lines.append("")

    # Cooling
    if state.cooling:
        lines.append("REGENERATIVE COOLING")
        lines.append("-" * 40)
        _add_param_str(lines, "Coolant", state.cooling.get("coolant", "—"))
        _add_param_str(lines, "Wall Material", state.cooling.get("wall_material", "—"))
        _add_param(lines, "Coolant Flow", state.cooling, "coolant_mass_flow", "kg/s")
        _add_param(lines, "Outlet Temp", state.cooling, "coolant_outlet_temp", "K")
        _add_param(lines, "Max Wall Temp", state.cooling, "max_wall_temperature", "K")
        _add_param(lines, "Max Heat Flux", state.cooling, "max_heat_flux", "MW/m²", 1e-6)
        _add_param(lines, "Total Heat Load", state.cooling, "total_heat_load", "kW", 1e-3)
        _add_param(lines, "Pressure Drop", state.cooling, "total_pressure_drop", "bar", 1e-5)
        lines.append("")

    # Feed system
    tank = state.feed_system.get("tank")
    if tank:
        lines.append("PROPELLANT TANK")
        lines.append("-" * 40)
        _add_param_str(lines, "Propellant", tank.get("propellant", "—"))
        _add_param(lines, "Propellant Mass", tank, "propellant_mass", "kg")
        _add_param(lines, "Total Volume", tank, "total_volume", "L", 1e3)
        _add_param(lines, "Tank Pressure", tank, "tank_pressure", "bar", 1e-5)
        _add_param(lines, "Wall Thickness", tank, "wall_thickness", "mm", 1e3)
        _add_param(lines, "Tank Mass", tank, "tank_mass", "kg")
        lines.append("")

    pressurant = state.feed_system.get("pressurant")
    if pressurant:
        lines.append("PRESSURANT SYSTEM")
        lines.append("-" * 40)
        _add_param_str(lines, "Gas", pressurant.get("gas", "—"))
        _add_param_str(lines, "Mode", pressurant.get("mode", "—"))
        _add_param(lines, "Gas Mass", pressurant, "pressurant_mass", "kg")
        _add_param(lines, "Bottle Volume", pressurant, "bottle_volume", "L", 1e3)
        _add_param(lines, "Initial Pressure", pressurant, "bottle_pressure_initial", "bar", 1e-5)
        lines.append("")

    lines.append(_hr)
    lines.append(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"  RESA Pro v{state.meta.version}")
    lines.append(_hr)

    return "\n".join(lines)


def _add_param(
    lines: list[str],
    label: str,
    data: dict[str, Any],
    key: str,
    unit: str = "",
    scale: float = 1.0,
) -> None:
    """Add a parameter line if the key exists in data."""
    val = data.get(key)
    if val is not None:
        scaled = val * scale
        unit_str = f" {unit}" if unit else ""
        if isinstance(scaled, float):
            lines.append(f"  {label:<20s} {scaled:>12.4f}{unit_str}")
        else:
            lines.append(f"  {label:<20s} {scaled!s:>12}{unit_str}")


def _add_param_str(lines: list[str], label: str, value: str) -> None:
    """Add a string parameter line."""
    lines.append(f"  {label:<20s} {value:>12}")


# --- HTML report ---


def generate_html_report(state: DesignState) -> str:
    """Generate an HTML design summary report.

    Produces a self-contained HTML document with inline CSS styling.

    Args:
        state: DesignState with design data.

    Returns:
        HTML string.
    """
    sections: list[str] = []

    # Header
    sections.append(_html_header(state))

    # Operating point
    rows = [
        ("Oxidizer", state.oxidizer, ""),
        ("Fuel", state.fuel, ""),
        ("Mixture Ratio", f"{state.mixture_ratio:.2f}", "O/F"),
        ("Chamber Pressure", f"{state.chamber_pressure / 1e5:.1f}", "bar"),
        ("Thrust", f"{state.thrust:.0f}", "N"),
    ]
    sections.append(_html_table("Operating Point", rows))

    # Chamber
    if state.chamber:
        ch = state.chamber
        rows = []
        _html_row(rows, "Throat Diameter", ch, "throat_diameter", "mm", 1e3)
        _html_row(rows, "Chamber Diameter", ch, "chamber_diameter", "mm", 1e3)
        _html_row(rows, "Chamber Length", ch, "chamber_length", "mm", 1e3)
        _html_row(rows, "Contraction Ratio", ch, "contraction_ratio", "")
        _html_row(rows, "L*", ch, "l_star", "m")
        _html_row(rows, "Chamber Volume", ch, "chamber_volume", "cm\u00b3", 1e6)
        _html_row(rows, "Mass Flow Rate", ch, "mass_flow", "kg/s")
        sections.append(_html_table("Chamber Geometry", rows))

    # Nozzle
    if state.nozzle:
        nz = state.nozzle
        rows = [("Method", str(nz.get("method", "")), "")]
        _html_row(rows, "Expansion Ratio", nz, "expansion_ratio", "")
        _html_row(rows, "Exit Radius", nz, "exit_radius", "mm", 1e3)
        _html_row(rows, "Nozzle Length", nz, "length", "mm", 1e3)
        _html_row(rows, "Div. Efficiency", nz, "divergence_efficiency", "")
        sections.append(_html_table("Nozzle Design", rows))

    # Performance
    if state.performance:
        perf = state.performance
        rows = []
        _html_row(rows, "c*", perf, "c_star", "m/s")
        _html_row(rows, "CF (vacuum)", perf, "CF_vac", "")
        _html_row(rows, "CF (sea level)", perf, "CF_sl", "")
        _html_row(rows, "Isp (vacuum)", perf, "Isp_vac", "s")
        _html_row(rows, "Isp (sea level)", perf, "Isp_sl", "s")
        _html_row(rows, "Exit Mach", perf, "exit_mach", "")
        sections.append(_html_table("Performance", rows))

    # Injector
    inj = state.feed_system.get("injector")
    if inj:
        rows = []
        _html_row(rows, "Oxidizer Flow", inj, "mass_flow_oxidizer", "kg/s")
        _html_row(rows, "Fuel Flow", inj, "mass_flow_fuel", "kg/s")
        _html_row(rows, "ΔP Oxidizer", inj, "dp_oxidizer", "bar", 1e-5)
        _html_row(rows, "ΔP Fuel", inj, "dp_fuel", "bar", 1e-5)
        _html_row(rows, "Elements (ox)", inj, "n_elements_ox", "")
        _html_row(rows, "Orifice Ø (ox)", inj, "element_diameter_ox", "mm", 1e3)
        _html_row(rows, "Elements (fuel)", inj, "n_elements_fuel", "")
        _html_row(rows, "Orifice Ø (fuel)", inj, "element_diameter_fuel", "mm", 1e3)
        sections.append(_html_table("Injector Design", rows))

    # Cooling
    if state.cooling:
        c = state.cooling
        rows = [
            ("Coolant", str(c.get("coolant", "")), ""),
            ("Wall Material", str(c.get("wall_material", "")), ""),
        ]
        _html_row(rows, "Coolant Flow", c, "coolant_mass_flow", "kg/s")
        _html_row(rows, "Outlet Temp", c, "coolant_outlet_temp", "K")
        _html_row(rows, "Max Wall Temp", c, "max_wall_temperature", "K")
        _html_row(rows, "Max Heat Flux", c, "max_heat_flux", "MW/m\u00b2", 1e-6)
        _html_row(rows, "Total Heat Load", c, "total_heat_load", "kW", 1e-3)
        _html_row(rows, "Pressure Drop", c, "total_pressure_drop", "bar", 1e-5)
        sections.append(_html_table("Regenerative Cooling", rows))

    # Footer
    sections.append(_html_footer(state))

    return "\n".join(sections)


def _html_header(state: DesignState) -> str:
    title = html_mod.escape(state.meta.name)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RESA Pro — {title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       max-width: 800px; margin: 2em auto; padding: 0 1em; color: #222; }}
h1 {{ color: #1a365d; border-bottom: 2px solid #2b6cb0; padding-bottom: 0.3em; }}
h2 {{ color: #2b6cb0; margin-top: 1.5em; }}
table {{ width: 100%; border-collapse: collapse; margin: 0.5em 0 1.5em; }}
th, td {{ text-align: left; padding: 0.4em 0.8em; border-bottom: 1px solid #e2e8f0; }}
th {{ background: #ebf4ff; color: #1a365d; }}
td:nth-child(2) {{ text-align: right; font-family: "SF Mono", "Fira Code", monospace; }}
td:nth-child(3) {{ color: #718096; font-size: 0.9em; }}
.footer {{ margin-top: 2em; padding-top: 1em; border-top: 1px solid #e2e8f0;
           color: #a0aec0; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>RESA Pro &mdash; Design Report</h1>
<p><strong>{title}</strong></p>
"""


def _html_table(title: str, rows: list[tuple[str, str, str]]) -> str:
    esc = html_mod.escape
    lines = [f"<h2>{esc(title)}</h2>", "<table>"]
    lines.append("<tr><th>Parameter</th><th>Value</th><th>Unit</th></tr>")
    for label, value, unit in rows:
        lines.append(f"<tr><td>{esc(label)}</td><td>{esc(value)}</td><td>{esc(unit)}</td></tr>")
    lines.append("</table>")
    return "\n".join(lines)


def _html_row(
    rows: list[tuple[str, str, str]],
    label: str,
    data: dict[str, Any],
    key: str,
    unit: str,
    scale: float = 1.0,
) -> None:
    val = data.get(key)
    if val is not None:
        scaled = val * scale
        if isinstance(scaled, float):
            rows.append((label, f"{scaled:.4f}", unit))
        else:
            rows.append((label, str(scaled), unit))


def _html_footer(state: DesignState) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<div class="footer">
Generated: {ts} &middot; RESA Pro v{html_mod.escape(state.meta.version)}
</div>
</body>
</html>"""


def save_text_report(state: DesignState, filepath: str) -> None:
    """Generate and save a plain-text report to a file."""
    report = generate_text_report(state)
    with open(filepath, "w") as f:
        f.write(report)


def save_html_report(state: DesignState, filepath: str) -> None:
    """Generate and save an HTML report to a file."""
    report = generate_html_report(state)
    with open(filepath, "w") as f:
        f.write(report)
