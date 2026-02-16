"""Tests for the 3D geometry generation module."""

import os
import tempfile

import numpy as np
import pytest

from resa_pro.geometry3d.engine import (
    RevolutionMesh,
    combine_contours,
    export_stl_ascii,
    export_stl_binary,
    revolve_contour,
)


class TestRevolveContour:
    """Test revolution body mesh generation."""

    def _simple_contour(self):
        """A simple cylinder: constant radius along x."""
        x = np.linspace(0, 0.1, 20)
        y = np.full_like(x, 0.02)
        return x, y

    def _cone_contour(self):
        """A simple cone: radius decreasing along x."""
        x = np.linspace(0, 0.1, 20)
        y = np.linspace(0.03, 0.015, 20)
        return x, y

    def test_basic_mesh_creation(self):
        x, y = self._simple_contour()
        mesh = revolve_contour(x, y, n_circumferential=16)
        assert isinstance(mesh, RevolutionMesh)
        assert mesh.n_vertices > 0
        assert mesh.n_faces > 0

    def test_vertex_count(self):
        """Vertex count = n_axial × n_circ + end caps."""
        x, y = self._simple_contour()
        n_circ = 16
        mesh = revolve_contour(x, y, n_circumferential=n_circ, close_ends=False)
        assert mesh.n_vertices == len(x) * n_circ

    def test_face_count_without_caps(self):
        """Face count = 2 × (n_axial - 1) × n_circ for quads → triangles."""
        x, y = self._simple_contour()
        n_circ = 16
        mesh = revolve_contour(x, y, n_circumferential=n_circ, close_ends=False)
        expected = 2 * (len(x) - 1) * n_circ
        assert mesh.n_faces == expected

    def test_close_ends_adds_faces(self):
        x, y = self._simple_contour()
        mesh_open = revolve_contour(x, y, n_circumferential=16, close_ends=False)
        mesh_closed = revolve_contour(x, y, n_circumferential=16, close_ends=True)
        assert mesh_closed.n_faces > mesh_open.n_faces

    def test_normals_shape(self):
        x, y = self._simple_contour()
        mesh = revolve_contour(x, y, n_circumferential=16)
        assert mesh.normals.shape == (mesh.n_faces, 3)

    def test_normals_unit_length(self):
        x, y = self._cone_contour()
        mesh = revolve_contour(x, y, n_circumferential=32)
        norms = np.linalg.norm(mesh.normals, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-6)

    def test_higher_circumferential_more_faces(self):
        x, y = self._simple_contour()
        mesh_16 = revolve_contour(x, y, n_circumferential=16)
        mesh_64 = revolve_contour(x, y, n_circumferential=64)
        assert mesh_64.n_faces > mesh_16.n_faces


class TestCombineContours:
    """Test chamber + nozzle contour combination."""

    def test_combine_basic(self):
        ch_x = np.linspace(0, 0.05, 20)
        ch_y = np.linspace(0.03, 0.015, 20)
        nz_x = np.linspace(0, 0.08, 30)
        nz_y = np.linspace(0.015, 0.04, 30)

        x, y = combine_contours(ch_x, ch_y, nz_x, nz_y)

        # Combined length should be 20 + 29 = 49 (skip 1 duplicate at throat)
        assert len(x) == 49
        assert len(y) == 49

    def test_continuity_at_throat(self):
        ch_x = np.linspace(0, 0.05, 20)
        ch_y = np.linspace(0.03, 0.015, 20)
        nz_x = np.linspace(0, 0.08, 30)
        nz_y = np.linspace(0.015, 0.04, 30)

        x, y = combine_contours(ch_x, ch_y, nz_x, nz_y)

        # The nozzle x starts at chamber end
        assert x[19] == pytest.approx(ch_x[-1], rel=1e-6)
        # The nozzle portion should continue from there
        assert x[20] > x[19]

    def test_monotonic_x(self):
        ch_x = np.linspace(0, 0.05, 20)
        ch_y = np.linspace(0.03, 0.015, 20)
        nz_x = np.linspace(0, 0.08, 30)
        nz_y = np.linspace(0.015, 0.04, 30)

        x, y = combine_contours(ch_x, ch_y, nz_x, nz_y)
        dx = np.diff(x)
        assert np.all(dx >= -1e-10)


class TestSTLExport:
    """Test STL file export."""

    def _make_mesh(self):
        x = np.linspace(0, 0.05, 10)
        y = np.full_like(x, 0.01)
        return revolve_contour(x, y, n_circumferential=8, close_ends=False)

    def test_binary_stl_creates_file(self):
        mesh = self._make_mesh()
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            path = f.name
        try:
            export_stl_binary(mesh, path)
            assert os.path.exists(path)
            size = os.path.getsize(path)
            # Binary STL: 80 header + 4 count + 50 bytes per face
            expected = 80 + 4 + 50 * mesh.n_faces
            assert size == expected
        finally:
            os.unlink(path)

    def test_ascii_stl_creates_file(self):
        mesh = self._make_mesh()
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False, mode="w") as f:
            path = f.name
        try:
            export_stl_ascii(mesh, path)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert content.startswith("solid engine")
            assert content.strip().endswith("endsolid engine")
            assert content.count("facet normal") == mesh.n_faces
        finally:
            os.unlink(path)
