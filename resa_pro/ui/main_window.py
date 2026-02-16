"""Main application window for RESA Pro GUI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from resa_pro import __app_name__, __version__
from resa_pro.ui.modules.chamber_tab import ChamberTab
from resa_pro.ui.modules.cooling_tab import CoolingFeedTab
from resa_pro.ui.modules.cycle_tab import CycleTab
from resa_pro.ui.modules.export_tab import ExportTab
from resa_pro.ui.modules.injector_tab import InjectorTab
from resa_pro.ui.modules.nozzle_tab import NozzleTab
from resa_pro.ui.modules.optimize_tab import OptimizeUQTab
from resa_pro.ui.modules.performance_tab import PerformanceTab
from resa_pro.ui.modules.thermal_tab import ThermalTab


class MainWindow(QMainWindow):
    """RESA Pro main application window.

    Provides a tabbed interface covering all engine design and analysis
    modules: chamber, nozzle, performance, thermal, injector, cooling,
    feed system, cycle analysis, optimization, UQ, and export.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(1100, 750)
        self.resize(1300, 850)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        # Add all module tabs
        self.tabs.addTab(ChamberTab(), "Chamber")
        self.tabs.addTab(NozzleTab(), "Nozzle")
        self.tabs.addTab(PerformanceTab(), "Performance")
        self.tabs.addTab(ThermalTab(), "Thermal")
        self.tabs.addTab(InjectorTab(), "Injector")
        self.tabs.addTab(CoolingFeedTab(), "Cooling & Feed")
        self.tabs.addTab(CycleTab(), "Cycle")
        self.tabs.addTab(OptimizeUQTab(), "Optimize & UQ")
        self.tabs.addTab(ExportTab(), "Export & Info")

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(f"{__app_name__} v{__version__} — Ready")

        # Menu bar
        self._build_menu()

    def _build_menu(self) -> None:
        menu = self.menuBar()

        # File menu
        file_menu = menu.addMenu("&File")

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menu.addMenu("&View")

        for i in range(self.tabs.count()):
            tab_name = self.tabs.tabText(i)
            action = QAction(f"&{tab_name}", self)
            idx = i  # capture
            action.triggered.connect(lambda checked, idx=idx: self.tabs.setCurrentIndex(idx))
            view_menu.addAction(action)

        # Help menu
        help_menu = menu.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _show_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            f"About {__app_name__}",
            f"<h3>{__app_name__} v{__version__}</h3>"
            f"<p>Rocket Engine Sizing and Analysis</p>"
            f"<p>A comprehensive tool for rocket engine design, analysis, "
            f"and optimisation built by Space Team Aachen.</p>"
            f"<p>MIT License</p>",
        )
