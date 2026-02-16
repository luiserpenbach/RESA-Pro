"""Plugin manager for RESA Pro.

Discovers, loads, validates, and manages lifecycle of plugins.
Supports filesystem-based discovery and entry-point-based registration.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from resa_pro.plugins.base import Plugin

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Metadata about a registered plugin."""

    name: str
    version: str
    description: str
    author: str
    module_path: str = ""
    enabled: bool = True
    instance: Plugin | None = None


class PluginManager:
    """Manages discovery, loading, and lifecycle of RESA Pro plugins.

    Plugins are Python classes that subclass ``Plugin`` and are discovered
    either from a directory scan or from registered entry points.

    Usage::

        manager = PluginManager()
        manager.discover("path/to/plugins/")
        manager.load_all()

        for name in manager.list_plugins():
            result = manager.run(name, engine_state)

    """

    def __init__(self) -> None:
        self._registry: dict[str, PluginInfo] = {}

    def register(self, plugin_cls: type[Plugin]) -> None:
        """Register a plugin class.

        Creates an instance and stores it in the registry.

        Args:
            plugin_cls: A subclass of Plugin.

        Raises:
            TypeError: If plugin_cls is not a subclass of Plugin.
            ValueError: If a plugin with the same name is already registered.
        """
        if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, Plugin)):
            raise TypeError(f"{plugin_cls} is not a subclass of Plugin")

        instance = plugin_cls()
        name = instance.name

        if name in self._registry:
            raise ValueError(f"Plugin '{name}' is already registered")

        self._registry[name] = PluginInfo(
            name=name,
            version=instance.version,
            description=instance.description,
            author=instance.author,
            instance=instance,
            enabled=True,
        )
        logger.info("Registered plugin: %s v%s", name, instance.version)

    def discover(self, directory: str | Path) -> int:
        """Discover and register plugins from a directory.

        Scans all ``.py`` files in the directory for classes that
        subclass ``Plugin``.

        Args:
            directory: Path to directory containing plugin modules.

        Returns:
            Number of plugins discovered.
        """
        directory = Path(directory)
        if not directory.is_dir():
            logger.warning("Plugin directory does not exist: %s", directory)
            return 0

        count = 0
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    f"resa_plugins.{py_file.stem}", py_file
                )
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Plugin)
                        and attr is not Plugin
                    ):
                        try:
                            self.register(attr)
                            count += 1
                        except (ValueError, TypeError) as e:
                            logger.warning("Skipping %s: %s", attr_name, e)

            except Exception as e:
                logger.warning("Failed to load plugin from %s: %s", py_file, e)

        logger.info("Discovered %d plugins in %s", count, directory)
        return count

    def discover_entry_points(self, group: str = "resa_pro.plugins") -> int:
        """Discover plugins registered via setuptools entry points.

        Args:
            group: Entry point group name.

        Returns:
            Number of plugins discovered.
        """
        count = 0
        try:
            if hasattr(importlib.metadata, "entry_points"):
                eps = importlib.metadata.entry_points()
                # Python 3.12+ returns a SelectableGroups; 3.10 returns a dict
                if isinstance(eps, dict):
                    entries = eps.get(group, [])
                else:
                    entries = eps.select(group=group)

                for ep in entries:
                    try:
                        plugin_cls = ep.load()
                        self.register(plugin_cls)
                        count += 1
                    except Exception as e:
                        logger.warning("Failed to load entry point %s: %s", ep.name, e)
        except Exception as e:
            logger.debug("Entry point discovery failed: %s", e)

        return count

    def unregister(self, name: str) -> None:
        """Remove a plugin from the registry.

        Args:
            name: Plugin name.

        Raises:
            KeyError: If plugin is not registered.
        """
        if name not in self._registry:
            raise KeyError(f"Plugin '{name}' is not registered")
        del self._registry[name]
        logger.info("Unregistered plugin: %s", name)

    def enable(self, name: str) -> None:
        """Enable a registered plugin."""
        self._get_info(name).enabled = True

    def disable(self, name: str) -> None:
        """Disable a registered plugin (keeps it registered)."""
        self._get_info(name).enabled = False

    def list_plugins(self) -> list[str]:
        """Return names of all registered plugins."""
        return list(self._registry.keys())

    def get_info(self, name: str) -> PluginInfo:
        """Get info about a registered plugin."""
        return self._get_info(name)

    def run(self, name: str, engine_state: dict[str, Any]) -> dict[str, Any]:
        """Execute a plugin's calculate method.

        Args:
            name: Plugin name.
            engine_state: Current engine design state.

        Returns:
            Plugin calculation results.

        Raises:
            KeyError: If plugin is not registered.
            RuntimeError: If plugin is disabled.
        """
        info = self._get_info(name)
        if not info.enabled:
            raise RuntimeError(f"Plugin '{name}' is disabled")
        if info.instance is None:
            raise RuntimeError(f"Plugin '{name}' has no instance")

        logger.info("Running plugin: %s", name)
        return info.instance.calculate(engine_state)

    def run_all(self, engine_state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Execute all enabled plugins.

        Args:
            engine_state: Current engine design state.

        Returns:
            Dict mapping plugin name → results.
        """
        results: dict[str, dict[str, Any]] = {}
        for name, info in self._registry.items():
            if info.enabled and info.instance is not None:
                try:
                    results[name] = info.instance.calculate(engine_state)
                except Exception as e:
                    logger.error("Plugin '%s' failed: %s", name, e)
                    results[name] = {"error": str(e)}
        return results

    def summary(self) -> list[dict[str, Any]]:
        """Return a summary of all registered plugins."""
        return [
            {
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "enabled": info.enabled,
            }
            for info in self._registry.values()
        ]

    def _get_info(self, name: str) -> PluginInfo:
        if name not in self._registry:
            raise KeyError(f"Plugin '{name}' is not registered")
        return self._registry[name]
