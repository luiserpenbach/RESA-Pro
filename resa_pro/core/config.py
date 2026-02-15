"""Design state management and project I/O for RESA Pro.

Handles saving/loading engine designs in JSON (metadata, config) and
HDF5 (large array data like contour points and simulation results).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Attempt HDF5 import; gracefully degrade if not installed
try:
    import h5py

    _HAS_H5PY = True
except ImportError:
    _HAS_H5PY = False
    logger.info("h5py not available — HDF5 features disabled")


# --- Project metadata ---


@dataclass
class ProjectMeta:
    """Top-level project metadata."""

    name: str = "Untitled"
    description: str = ""
    author: str = ""
    version: str = "0.1.0"
    created: str = ""
    modified: str = ""
    unit_system: str = "SI"  # "SI" or "imperial"

    def touch(self) -> None:
        """Update the modified timestamp."""
        self.modified = datetime.now(timezone.utc).isoformat()


@dataclass
class DesignState:
    """Complete engine design state.

    This is the single source of truth passed between modules and
    persisted to disk.
    """

    meta: ProjectMeta = field(default_factory=ProjectMeta)

    # Operating point
    oxidizer: str = "n2o"
    fuel: str = "ethanol"
    mixture_ratio: float = 4.0
    chamber_pressure: float = 2.0e6  # Pa
    thrust: float = 2000.0  # N

    # Chamber geometry (populated by chamber module)
    chamber: dict[str, Any] = field(default_factory=dict)

    # Nozzle (populated by nozzle module)
    nozzle: dict[str, Any] = field(default_factory=dict)

    # Cooling (populated by cooling module)
    cooling: dict[str, Any] = field(default_factory=dict)

    # Feed system
    feed_system: dict[str, Any] = field(default_factory=dict)

    # Performance summary
    performance: dict[str, Any] = field(default_factory=dict)

    # Array data stored separately in HDF5
    _array_data: dict[str, np.ndarray] = field(default_factory=dict, repr=False)


# --- JSON serialization ---


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        return super().default(obj)


def save_design_json(state: DesignState, path: str | Path) -> None:
    """Save design state to a JSON file (excludes large arrays).

    Arrays stored in _array_data are written to a companion HDF5 file
    if h5py is available.
    """
    path = Path(path)
    state.meta.touch()

    # Serialise the dataclass, skipping _array_data
    data = asdict(state)
    data.pop("_array_data", None)

    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=_NumpyEncoder)

    logger.info("Saved design to %s", path)

    # Optionally write arrays to HDF5
    if _HAS_H5PY and state._array_data:
        h5_path = path.with_suffix(".h5")
        save_arrays_hdf5(state._array_data, h5_path)


def load_design_json(path: str | Path) -> DesignState:
    """Load design state from a JSON file.

    If a companion .h5 file exists, array data is also loaded.
    """
    path = Path(path)
    with open(path) as f:
        data = json.load(f)

    meta = ProjectMeta(**data.pop("meta", {}))
    state = DesignState(meta=meta, **data)

    # Load companion HDF5 if present
    h5_path = path.with_suffix(".h5")
    if _HAS_H5PY and h5_path.exists():
        state._array_data = load_arrays_hdf5(h5_path)

    return state


# --- HDF5 helpers ---


def save_arrays_hdf5(arrays: dict[str, np.ndarray], path: str | Path) -> None:
    """Save a dictionary of numpy arrays to HDF5."""
    if not _HAS_H5PY:
        logger.warning("h5py not available, skipping HDF5 save")
        return
    path = Path(path)
    with h5py.File(path, "w") as f:
        for key, arr in arrays.items():
            f.create_dataset(key, data=arr)
        f.attrs["created"] = datetime.now(timezone.utc).isoformat()
    logger.info("Saved %d arrays to %s", len(arrays), path)


def load_arrays_hdf5(path: str | Path) -> dict[str, np.ndarray]:
    """Load all datasets from an HDF5 file into a dictionary."""
    if not _HAS_H5PY:
        logger.warning("h5py not available, skipping HDF5 load")
        return {}
    path = Path(path)
    arrays: dict[str, np.ndarray] = {}
    with h5py.File(path, "r") as f:
        for key in f.keys():
            arrays[key] = f[key][:]
    return arrays
