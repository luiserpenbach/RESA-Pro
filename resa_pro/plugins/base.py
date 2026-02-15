"""Base class for RESA Pro plugins.

All plugins should subclass ``Plugin`` and implement the required methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Plugin(ABC):
    """Abstract base class for RESA Pro plugins.

    Plugins extend RESA Pro with additional analysis capabilities,
    UI tabs, or CLI commands.
    """

    # Plugin metadata — override in subclasses
    name: str = "unnamed_plugin"
    version: str = "0.1.0"
    description: str = ""
    author: str = ""

    @abstractmethod
    def calculate(self, engine_state: dict[str, Any]) -> dict[str, Any]:
        """Perform plugin-specific calculations.

        Args:
            engine_state: Current engine design state dictionary.

        Returns:
            Dictionary of calculated results.
        """
        ...

    def add_ui_tab(self, parent_widget: Any) -> None:
        """Optional: add a UI tab to the main application.

        Override this to provide a PySide6 widget.
        """

    def add_cli_command(self, cli_group: Any) -> None:
        """Optional: register CLI commands.

        Override this to add Click commands.
        """
