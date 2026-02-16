"""Main application window for RESA Pro GUI."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal, QObject
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


class SharedState(QObject):
    """Shared design state that allows tabs to exchange results.

    Tabs publish their computed results via ``update(key, value)`` and
    other tabs can read them via ``get(key)``.  The ``changed`` signal
    is emitted whenever a value is updated.
    """

    changed = Signal(str)  # emits the key that was updated

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[str, Any] = {}

    def update(self, key: str, value: Any) -> None:
        """Store *value* under *key* and notify listeners."""
        self._data[key] = value
        self.changed.emit(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a previously stored value."""
        return self._data.get(key, default)

    def keys(self) -> list[str]:
        return list(self._data.keys())


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

        # Shared state across tabs
        self.shared = SharedState()

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

        # Add all module tabs — pass shared state where applicable
        self.chamber_tab = ChamberTab(shared=self.shared)
        self.nozzle_tab = NozzleTab()
        self.performance_tab = PerformanceTab()
        self.thermal_tab = ThermalTab()
        self.injector_tab = InjectorTab()
        self.cooling_tab = CoolingFeedTab()
        self.cycle_tab = CycleTab()
        self.optimize_tab = OptimizeUQTab()
        self.export_tab = ExportTab()

        self.tabs.addTab(self.chamber_tab, "Chamber")
        self.tabs.addTab(self.nozzle_tab, "Nozzle")
        self.tabs.addTab(self.performance_tab, "Performance")
        self.tabs.addTab(self.thermal_tab, "Thermal")
        self.tabs.addTab(self.injector_tab, "Injector")
        self.tabs.addTab(self.cooling_tab, "Cooling & Feed")
        self.tabs.addTab(self.cycle_tab, "Cycle")
        self.tabs.addTab(self.optimize_tab, "Optimize & UQ")
        self.tabs.addTab(self.export_tab, "Export & Info")

        # Update status bar on shared state changes
        self.shared.changed.connect(self._on_state_changed)

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

    def _on_state_changed(self, key: str) -> None:
        self.status.showMessage(f"Updated: {key}", 3000)

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
