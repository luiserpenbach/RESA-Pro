"""RESA Pro GUI application entry point.

Launch with:
    python -m resa_pro.ui.app
    resa gui           (via CLI command)
"""

from __future__ import annotations

import sys


def run() -> None:
    """Launch the RESA Pro desktop application."""
    from PySide6.QtWidgets import QApplication

    from resa_pro.ui.main_window import MainWindow
    from resa_pro.ui.styles.theme import STYLESHEET

    app = QApplication(sys.argv)
    app.setApplicationName("RESA Pro")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
