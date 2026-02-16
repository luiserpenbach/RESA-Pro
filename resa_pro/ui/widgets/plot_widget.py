"""Matplotlib-based plot widget for PySide6."""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import QVBoxLayout, QWidget


class PlotCanvas(QWidget):
    """Embeddable matplotlib figure canvas.

    Usage::

        plot = PlotCanvas(title="Contour")
        plot.plot(x, y, xlabel="x [m]", ylabel="r [m]")
        plot.plot_multi([(x1, y1, "series1"), (x2, y2, "series2")])
    """

    def __init__(
        self,
        title: str = "",
        parent: QWidget | None = None,
        figsize: tuple[float, float] = (5.0, 3.5),
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(figsize=figsize, dpi=100)
        self._canvas = FigureCanvas(self._figure)
        layout.addWidget(self._canvas)

        self._ax = self._figure.add_subplot(111)
        if title:
            self._ax.set_title(title, fontsize=10)
        self._figure.tight_layout()

    @property
    def ax(self):
        return self._ax

    @property
    def figure(self):
        return self._figure

    def clear(self) -> None:
        """Clear the axes."""
        self._ax.clear()
        self._canvas.draw()

    def plot(
        self,
        x: np.ndarray | list,
        y: np.ndarray | list,
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        color: str = "steelblue",
        linewidth: float = 1.5,
    ) -> None:
        """Plot a single line."""
        self._ax.clear()
        self._ax.plot(x, y, color=color, linewidth=linewidth)
        if xlabel:
            self._ax.set_xlabel(xlabel, fontsize=9)
        if ylabel:
            self._ax.set_ylabel(ylabel, fontsize=9)
        if title:
            self._ax.set_title(title, fontsize=10)
        self._ax.grid(True, alpha=0.3)
        self._ax.tick_params(labelsize=8)
        self._figure.tight_layout()
        self._canvas.draw()

    def plot_multi(
        self,
        series: list[tuple],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
    ) -> None:
        """Plot multiple series: [(x, y, label), ...]."""
        self._ax.clear()
        colors = ["steelblue", "coral", "seagreen", "orchid", "goldenrod", "slategray"]
        for i, item in enumerate(series):
            x, y, label = item[0], item[1], item[2] if len(item) > 2 else f"series {i}"
            self._ax.plot(x, y, label=label, color=colors[i % len(colors)], linewidth=1.5)
        if xlabel:
            self._ax.set_xlabel(xlabel, fontsize=9)
        if ylabel:
            self._ax.set_ylabel(ylabel, fontsize=9)
        if title:
            self._ax.set_title(title, fontsize=10)
        self._ax.grid(True, alpha=0.3)
        self._ax.legend(fontsize=8)
        self._ax.tick_params(labelsize=8)
        self._figure.tight_layout()
        self._canvas.draw()

    def bar(
        self,
        labels: list[str],
        values: list[float],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        color: str = "steelblue",
    ) -> None:
        """Draw a bar chart."""
        self._ax.clear()
        x = range(len(labels))
        self._ax.bar(x, values, color=color, alpha=0.8)
        self._ax.set_xticks(x)
        self._ax.set_xticklabels(labels, fontsize=8, rotation=30, ha="right")
        if xlabel:
            self._ax.set_xlabel(xlabel, fontsize=9)
        if ylabel:
            self._ax.set_ylabel(ylabel, fontsize=9)
        if title:
            self._ax.set_title(title, fontsize=10)
        self._ax.grid(True, alpha=0.3, axis="y")
        self._figure.tight_layout()
        self._canvas.draw()

    def scatter(
        self,
        x: np.ndarray | list,
        y: np.ndarray | list,
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        color: str = "steelblue",
        size: float = 15,
    ) -> None:
        """Draw a scatter plot."""
        self._ax.clear()
        self._ax.scatter(x, y, c=color, s=size, alpha=0.6, edgecolors="none")
        if xlabel:
            self._ax.set_xlabel(xlabel, fontsize=9)
        if ylabel:
            self._ax.set_ylabel(ylabel, fontsize=9)
        if title:
            self._ax.set_title(title, fontsize=10)
        self._ax.grid(True, alpha=0.3)
        self._ax.tick_params(labelsize=8)
        self._figure.tight_layout()
        self._canvas.draw()
