"""Export & Reports tab — 3D STL export, report generation, and database info."""

from __future__ import annotations

import traceback
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from resa_pro.ui.widgets.param_input import ParamForm
from resa_pro.ui.widgets.plot_widget import PlotCanvas
from resa_pro.ui.widgets.result_display import LogPanel, ResultTable


class ExportTab(QWidget):
    """3D export, reports, and database information tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        tabs = QTabWidget()
        tabs.addTab(self._build_stl_panel(), "3D STL Export")
        tabs.addTab(self._build_info_panel(), "Propellants & Materials")
        layout.addWidget(tabs)

    # ---------- STL Export ----------

    def _build_stl_panel(self) -> QWidget:
        w = QWidget()
        splitter = QSplitter()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        self.stl_form = ParamForm()
        self.stl_form.add_header("Engine Geometry")
        self.stl_form.add_float("throat_radius", "Throat Radius", 15.0, unit="mm", min_val=1, max_val=500, step=0.5)
        self.stl_form.add_float("expansion_ratio", "Expansion Ratio", 10.0, min_val=1.5, max_val=100, step=0.5)
        self.stl_form.add_float("contraction_ratio", "Contraction Ratio", 3.5, min_val=1.2, max_val=10, step=0.1)
        self.stl_form.add_float("l_star", "L*", 1.2, unit="m", min_val=0.2, max_val=5.0, step=0.05)
        self.stl_form.add_combo("nozzle_type", "Nozzle Type", ["parabolic", "conical"], default="parabolic")
        self.stl_form.add_int("n_circ", "Circumferential Divisions", 64, min_val=8, max_val=256)

        scroll = QScrollArea()
        scroll.setWidget(self.stl_form)
        scroll.setWidgetResizable(True)
        ll.addWidget(scroll)

        btn_preview = QPushButton("Preview Contour")
        btn_preview.clicked.connect(self._preview_contour)
        ll.addWidget(btn_preview)

        btn_export = QPushButton("Export STL...")
        btn_export.setProperty("secondary", True)
        btn_export.clicked.connect(self._export_stl)
        ll.addWidget(btn_export)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.stl_results = ResultTable("Mesh Info")
        rl.addWidget(self.stl_results)
        self.stl_plot = PlotCanvas("Engine Profile")
        rl.addWidget(self.stl_plot)
        self.stl_log = LogPanel("Log")
        self.stl_log.setMaximumHeight(80)
        rl.addWidget(self.stl_log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([350, 650])
        return w

    # ---------- Info Panel ----------

    def _build_info_panel(self) -> QWidget:
        w = QWidget()
        splitter = QSplitter()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        btn_prop = QPushButton("Show Propellants")
        btn_prop.clicked.connect(self._show_propellants)
        ll.addWidget(btn_prop)

        btn_mat = QPushButton("Show Materials")
        btn_mat.setProperty("secondary", True)
        btn_mat.clicked.connect(self._show_materials)
        ll.addWidget(btn_mat)

        ll.addStretch()

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.info_results = ResultTable("Database")
        rl.addWidget(self.info_results)
        self.info_log = LogPanel("Log")
        self.info_log.setMaximumHeight(80)
        rl.addWidget(self.info_log)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([200, 800])
        return w

    # ---------- Callbacks ----------

    def _get_contour(self):
        v = self.stl_form.get_values()
        from resa_pro.core.chamber import size_chamber_from_dimensions, generate_chamber_contour
        from resa_pro.core.nozzle import conical_nozzle, parabolic_nozzle
        from resa_pro.geometry3d.engine import combine_contours

        throat_r = v["throat_radius"] / 1e3
        geom = size_chamber_from_dimensions(
            throat_diameter=throat_r * 2,
            contraction_ratio=v["contraction_ratio"],
            l_star=v["l_star"],
        )
        cx, cy = generate_chamber_contour(geom)

        if v["nozzle_type"] == "conical":
            noz = conical_nozzle(throat_r, v["expansion_ratio"])
        else:
            noz = parabolic_nozzle(throat_r, v["expansion_ratio"])

        full_x, full_y = combine_contours(list(cx), list(cy), list(noz.x), list(noz.y))
        return full_x, full_y, v

    def _preview_contour(self) -> None:
        self.stl_log.clear()
        self.stl_results.clear()
        try:
            full_x, full_y, v = self._get_contour()

            x_mm = np.array(full_x) * 1e3
            y_mm = np.array(full_y) * 1e3

            self.stl_plot.ax.clear()
            self.stl_plot.ax.plot(x_mm, y_mm, color="steelblue", linewidth=1.5)
            self.stl_plot.ax.plot(x_mm, -y_mm, color="steelblue", linewidth=1.5)
            self.stl_plot.ax.fill_between(x_mm, -y_mm, y_mm, alpha=0.1, color="steelblue")
            self.stl_plot.ax.set_xlabel("x [mm]", fontsize=9)
            self.stl_plot.ax.set_ylabel("r [mm]", fontsize=9)
            self.stl_plot.ax.set_title("Engine Profile", fontsize=10)
            self.stl_plot.ax.set_aspect("equal")
            self.stl_plot.ax.grid(True, alpha=0.3)
            self.stl_plot.figure.tight_layout()
            self.stl_plot._canvas.draw()

            rows = [
                ("Total Length", f"{(max(full_x) - min(full_x)) * 1e3:.1f}", "mm"),
                ("Max Radius", f"{max(full_y) * 1e3:.1f}", "mm"),
                ("Contour Points", f"{len(full_x)}", ""),
            ]
            self.stl_results.set_data(rows)
            self.stl_log.log("Contour preview generated")

        except Exception as e:
            self.stl_log.log(f"ERROR: {e}")
            self.stl_log.log(traceback.format_exc())

    def _export_stl(self) -> None:
        self.stl_log.clear()
        try:
            full_x, full_y, v = self._get_contour()
            from resa_pro.geometry3d.engine import revolve_contour, export_stl_binary

            mesh = revolve_contour(full_x, full_y, n_circumferential=v["n_circ"])

            filepath, _ = QFileDialog.getSaveFileName(self, "Export STL", "engine.stl", "STL Files (*.stl)")
            if filepath:
                export_stl_binary(mesh, filepath)
                rows = [
                    ("Vertices", f"{mesh.n_vertices}", ""),
                    ("Faces", f"{mesh.n_faces}", ""),
                    ("File", filepath, ""),
                ]
                self.stl_results.set_data(rows)
                self.stl_log.log(f"Exported: {filepath} ({mesh.n_faces} faces)")

        except Exception as e:
            self.stl_log.log(f"ERROR: {e}")
            self.stl_log.log(traceback.format_exc())

    def _show_propellants(self) -> None:
        self.info_log.clear()
        self.info_results.clear()
        try:
            from resa_pro.core.fluids import list_propellants, get_propellant_info

            props = list_propellants()
            rows = []
            for name in props:
                info = get_propellant_info(name)
                rows.append((
                    name,
                    info.get("type", "?"),
                    f"M={info.get('molar_mass', 0)*1e3:.1f} g/mol",
                ))
            self.info_results.set_title("Propellant Database")
            self.info_results.set_data(rows)
            self.info_log.log(f"Loaded {len(props)} propellants")

        except Exception as e:
            self.info_log.log(f"ERROR: {e}")

    def _show_materials(self) -> None:
        self.info_log.clear()
        self.info_results.clear()
        try:
            from resa_pro.core.materials import list_materials, get_material_info

            mats = list_materials()
            rows = []
            for mid in mats:
                info = get_material_info(mid)
                rows.append((
                    info.get("name", mid),
                    info.get("category", "?"),
                    f"rho={info.get('density', 0):.0f} kg/m3",
                ))
            self.info_results.set_title("Material Database")
            self.info_results.set_data(rows)
            self.info_log.log(f"Loaded {len(mats)} materials")

        except Exception as e:
            self.info_log.log(f"ERROR: {e}")
