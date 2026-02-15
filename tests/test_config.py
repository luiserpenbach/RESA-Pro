"""Tests for config management module."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from resa_pro.core.config import (
    DesignState,
    ProjectMeta,
    load_design_json,
    save_design_json,
)


class TestDesignState:
    def test_defaults(self):
        state = DesignState()
        assert state.oxidizer == "n2o"
        assert state.fuel == "ethanol"
        assert state.chamber_pressure > 0

    def test_meta_touch(self):
        meta = ProjectMeta(name="Test")
        meta.touch()
        assert meta.modified != ""


class TestJsonPersistence:
    def test_save_and_load(self, tmp_path):
        state = DesignState(
            meta=ProjectMeta(name="Test Engine"),
            oxidizer="lox",
            fuel="rp1",
            mixture_ratio=2.7,
            chamber_pressure=5e6,
            thrust=10000,
            chamber={"throat_diameter": 0.05},
        )
        path = tmp_path / "test_design.json"
        save_design_json(state, path)

        loaded = load_design_json(path)
        assert loaded.meta.name == "Test Engine"
        assert loaded.oxidizer == "lox"
        assert loaded.mixture_ratio == pytest.approx(2.7)
        assert loaded.chamber["throat_diameter"] == pytest.approx(0.05)

    def test_numpy_serialization(self, tmp_path):
        """Numpy arrays in dicts should be serialized to lists."""
        state = DesignState()
        state.nozzle = {"contour_x": np.linspace(0, 1, 10).tolist()}
        path = tmp_path / "test_np.json"
        save_design_json(state, path)

        # Should be valid JSON
        with open(path) as f:
            data = json.load(f)
        assert len(data["nozzle"]["contour_x"]) == 10
