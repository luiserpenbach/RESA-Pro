"""Reusable result display widgets for RESA Pro GUI.

Provides table-based result views and log/status output panels.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ResultTable(QWidget):
    """Three-column result table: Parameter | Value | Unit."""

    def __init__(self, title: str = "Results", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel(f"<b>{title}</b>")
        layout.addWidget(self._title_label)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Parameter", "Value", "Unit"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

    def set_title(self, title: str) -> None:
        self._title_label.setText(f"<b>{title}</b>")

    def clear(self) -> None:
        self._table.setRowCount(0)

    def set_data(self, rows: list[tuple[str, str, str]]) -> None:
        """Set table data from a list of (name, value, unit) tuples."""
        self._table.setRowCount(len(rows))
        for i, (name, value, unit) in enumerate(rows):
            name_item = QTableWidgetItem(name)
            value_item = QTableWidgetItem(value)
            unit_item = QTableWidgetItem(unit)
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(i, 0, name_item)
            self._table.setItem(i, 1, value_item)
            self._table.setItem(i, 2, unit_item)

    def add_row(self, name: str, value: str, unit: str = "") -> None:
        """Append a single row."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(name))
        val_item = QTableWidgetItem(value)
        val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, 1, val_item)
        self._table.setItem(row, 2, QTableWidgetItem(unit))

    def add_section(self, header: str) -> None:
        """Add a bold section header row spanning all columns."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        item = QTableWidgetItem(header)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self._table.setItem(row, 0, item)
        self._table.setItem(row, 1, QTableWidgetItem(""))
        self._table.setItem(row, 2, QTableWidgetItem(""))


class LogPanel(QWidget):
    """Read-only text log for status messages."""

    def __init__(self, title: str = "Log", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel(f"<b>{title}</b>")
        layout.addWidget(self._title_label)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(500)
        font = QFont("Consolas, Courier New, monospace", 9)
        self._text.setFont(font)
        layout.addWidget(self._text)

    def log(self, message: str) -> None:
        self._text.appendPlainText(message)

    def clear(self) -> None:
        self._text.clear()
