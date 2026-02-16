"""Tests for the plugin manager."""

import pytest

from resa_pro.plugins.base import Plugin
from resa_pro.plugins.manager import PluginManager


class DummyPlugin(Plugin):
    """A minimal test plugin."""

    name = "dummy"
    version = "1.0.0"
    description = "A dummy test plugin"
    author = "Test"

    def calculate(self, engine_state):
        thrust = engine_state.get("thrust", 0)
        return {"doubled_thrust": thrust * 2}


class AnotherPlugin(Plugin):
    """Second test plugin."""

    name = "another"
    version = "0.5.0"
    description = "Another test plugin"
    author = "Test"

    def calculate(self, engine_state):
        return {"constant": 42}


class TestPluginManager:
    """Test the plugin manager."""

    def test_register(self):
        pm = PluginManager()
        pm.register(DummyPlugin)

        assert "dummy" in pm.list_plugins()
        info = pm.get_info("dummy")
        assert info.version == "1.0.0"
        assert info.enabled is True

    def test_register_not_plugin(self):
        pm = PluginManager()
        with pytest.raises(TypeError):
            pm.register(str)  # type: ignore

    def test_register_duplicate(self):
        pm = PluginManager()
        pm.register(DummyPlugin)
        with pytest.raises(ValueError, match="already registered"):
            pm.register(DummyPlugin)

    def test_unregister(self):
        pm = PluginManager()
        pm.register(DummyPlugin)
        pm.unregister("dummy")
        assert "dummy" not in pm.list_plugins()

    def test_unregister_unknown(self):
        pm = PluginManager()
        with pytest.raises(KeyError):
            pm.unregister("nonexistent")

    def test_enable_disable(self):
        pm = PluginManager()
        pm.register(DummyPlugin)

        pm.disable("dummy")
        assert pm.get_info("dummy").enabled is False

        pm.enable("dummy")
        assert pm.get_info("dummy").enabled is True

    def test_run_plugin(self):
        pm = PluginManager()
        pm.register(DummyPlugin)

        result = pm.run("dummy", {"thrust": 500})
        assert result["doubled_thrust"] == 1000

    def test_run_disabled_raises(self):
        pm = PluginManager()
        pm.register(DummyPlugin)
        pm.disable("dummy")

        with pytest.raises(RuntimeError, match="disabled"):
            pm.run("dummy", {})

    def test_run_unknown_raises(self):
        pm = PluginManager()
        with pytest.raises(KeyError):
            pm.run("nonexistent", {})

    def test_run_all(self):
        pm = PluginManager()
        pm.register(DummyPlugin)
        pm.register(AnotherPlugin)

        results = pm.run_all({"thrust": 100})

        assert "dummy" in results
        assert "another" in results
        assert results["dummy"]["doubled_thrust"] == 200
        assert results["another"]["constant"] == 42

    def test_run_all_skips_disabled(self):
        pm = PluginManager()
        pm.register(DummyPlugin)
        pm.register(AnotherPlugin)
        pm.disable("another")

        results = pm.run_all({"thrust": 100})

        assert "dummy" in results
        assert "another" not in results

    def test_summary(self):
        pm = PluginManager()
        pm.register(DummyPlugin)

        summaries = pm.summary()
        assert len(summaries) == 1
        assert summaries[0]["name"] == "dummy"
        assert summaries[0]["version"] == "1.0.0"

    def test_discover_directory(self, tmp_path):
        """Test filesystem discovery."""
        # Write a plugin file
        plugin_code = '''
from resa_pro.plugins.base import Plugin

class TempPlugin(Plugin):
    name = "temp_plugin"
    version = "0.1.0"
    description = "Temporary"
    author = "Test"

    def calculate(self, engine_state):
        return {"status": "ok"}
'''
        plugin_file = tmp_path / "temp_plugin.py"
        plugin_file.write_text(plugin_code)

        pm = PluginManager()
        count = pm.discover(tmp_path)

        assert count == 1
        assert "temp_plugin" in pm.list_plugins()

    def test_discover_nonexistent_dir(self):
        pm = PluginManager()
        count = pm.discover("/nonexistent/path")
        assert count == 0


class TestMassEstimatorPlugin:
    """Test the built-in mass estimator example plugin."""

    def test_mass_estimator(self):
        from resa_pro.plugins.examples.mass_estimator import MassEstimatorPlugin

        pm = PluginManager()
        pm.register(MassEstimatorPlugin)

        result = pm.run("mass_estimator", {
            "thrust": 2000.0,
            "chamber_pressure": 2e6,
            "expansion_ratio": 10.0,
        })

        assert "total_dry_mass_kg" in result
        assert result["total_dry_mass_kg"] > 0
        assert "thrust_to_weight" in result
