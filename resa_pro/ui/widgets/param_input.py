"""Reusable parameter input form builder for RESA Pro GUI.

Provides a declarative way to build input forms with validated fields,
combo boxes, and group boxes.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ParamForm(QWidget):
    """Declarative parameter input form.

    Usage::

        form = ParamForm()
        form.add_float("thrust", "Thrust", 2000.0, unit="N", min_val=0, max_val=1e8)
        form.add_combo("oxidizer", "Oxidizer", ["n2o", "lox", "h2o2"])
        form.add_int("n_elements", "Elements", 12, min_val=1, max_val=1000)
        values = form.get_values()
    """

    value_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QFormLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)
        self._fields: dict[str, QWidget] = {}
        self._types: dict[str, str] = {}

    def add_header(self, text: str) -> None:
        """Add a bold header label."""
        label = QLabel(f"<b>{text}</b>")
        self._layout.addRow(label)

    def add_separator(self) -> None:
        """Add a visual separator line."""
        line = QLabel("")
        line.setFixedHeight(8)
        self._layout.addRow(line)

    def add_float(
        self,
        name: str,
        label: str,
        default: float = 0.0,
        *,
        unit: str = "",
        min_val: float = -1e15,
        max_val: float = 1e15,
        decimals: int = 4,
        step: float = 0.0,
    ) -> QDoubleSpinBox:
        """Add a floating-point input field."""
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setValue(default)
        spin.setMinimumWidth(140)
        if step > 0:
            spin.setSingleStep(step)
        else:
            spin.setSingleStep(default * 0.1 if default != 0 else 1.0)
        spin.valueChanged.connect(self.value_changed.emit)

        lbl = f"{label}" if not unit else f"{label} [{unit}]"
        self._layout.addRow(lbl, spin)
        self._fields[name] = spin
        self._types[name] = "float"
        return spin

    def add_int(
        self,
        name: str,
        label: str,
        default: int = 0,
        *,
        unit: str = "",
        min_val: int = 0,
        max_val: int = 999999,
    ) -> QSpinBox:
        """Add an integer input field."""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setMinimumWidth(140)
        spin.valueChanged.connect(self.value_changed.emit)

        lbl = f"{label}" if not unit else f"{label} [{unit}]"
        self._layout.addRow(lbl, spin)
        self._fields[name] = spin
        self._types[name] = "int"
        return spin

    def add_combo(
        self,
        name: str,
        label: str,
        options: list[str],
        default: str | None = None,
    ) -> QComboBox:
        """Add a combo-box selection field."""
        combo = QComboBox()
        combo.addItems(options)
        combo.setMinimumWidth(140)
        if default and default in options:
            combo.setCurrentText(default)
        combo.currentTextChanged.connect(lambda _: self.value_changed.emit())

        self._layout.addRow(label, combo)
        self._fields[name] = combo
        self._types[name] = "combo"
        return combo

    def get_values(self) -> dict[str, Any]:
        """Return all current field values as a dictionary."""
        values: dict[str, Any] = {}
        for name, widget in self._fields.items():
            t = self._types[name]
            if t == "float":
                values[name] = widget.value()
            elif t == "int":
                values[name] = widget.value()
            elif t == "combo":
                values[name] = widget.currentText()
        return values

    def get(self, name: str) -> Any:
        """Get a single field value."""
        widget = self._fields[name]
        t = self._types[name]
        if t == "float":
            return widget.value()
        elif t == "int":
            return widget.value()
        elif t == "combo":
            return widget.currentText()
        return None

    def set_value(self, name: str, value: Any) -> None:
        """Set a field value programmatically."""
        widget = self._fields[name]
        t = self._types[name]
        if t == "float":
            widget.setValue(float(value))
        elif t == "int":
            widget.setValue(int(value))
        elif t == "combo":
            widget.setCurrentText(str(value))
