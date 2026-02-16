"""3D geometry generation module for RESA Pro.

Generates axisymmetric revolution bodies from 2D contour profiles
(chamber + nozzle).  Exports to STL for CAD import or visualization.

Uses numpy-only surface generation.  CADQuery/trimesh are optional
dependencies used only for STL export.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from resa_pro.utils.constants import PI, TWO_PI


@dataclass
class RevolutionMesh:
    """Triangulated surface mesh of an axisymmetric body.

    The mesh is stored as vertex and face arrays, compatible with
    standard 3D formats (STL, OBJ).
    """

    vertices: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))  # (N, 3)
    faces: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=int))  # (M, 3)
    normals: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))  # (M, 3)

    @property
    def n_vertices(self) -> int:
        return len(self.vertices)

    @property
    def n_faces(self) -> int:
        return len(self.faces)


def revolve_contour(
    contour_x: np.ndarray,
    contour_y: np.ndarray,
    n_circumferential: int = 64,
    close_ends: bool = True,
) -> RevolutionMesh:
    """Create a 3D revolution body from a 2D axisymmetric contour.

    Revolves the contour (x, y) around the x-axis to produce a
    triangulated surface mesh.

    Args:
        contour_x: Axial positions [m].
        contour_y: Radii [m] (distance from axis).
        n_circumferential: Number of divisions around the circumference.
        close_ends: If True, close the front and rear faces with fan triangles.

    Returns:
        RevolutionMesh with vertices and face indices.
    """
    n_axial = len(contour_x)
    n_circ = n_circumferential
    theta = np.linspace(0, TWO_PI, n_circ, endpoint=False)

    # Generate vertices: each axial station × each circumferential angle
    # Shape: (n_axial * n_circ, 3)
    vertices = np.zeros((n_axial * n_circ, 3))
    for i in range(n_axial):
        x = contour_x[i]
        r = contour_y[i]
        for j in range(n_circ):
            idx = i * n_circ + j
            vertices[idx, 0] = x
            vertices[idx, 1] = r * np.cos(theta[j])
            vertices[idx, 2] = r * np.sin(theta[j])

    # Generate faces (two triangles per quad)
    faces = []
    for i in range(n_axial - 1):
        for j in range(n_circ):
            j_next = (j + 1) % n_circ
            # Indices of the four corners of the quad
            v00 = i * n_circ + j
            v01 = i * n_circ + j_next
            v10 = (i + 1) * n_circ + j
            v11 = (i + 1) * n_circ + j_next

            # Two triangles
            faces.append([v00, v10, v01])
            faces.append([v01, v10, v11])

    # Close ends with fan triangulation
    if close_ends:
        # Front face (at contour_x[0])
        if contour_y[0] > 1e-10:
            center_front = len(vertices)
            cx = contour_x[0]
            vertices = np.vstack([vertices, [[cx, 0.0, 0.0]]])
            for j in range(n_circ):
                j_next = (j + 1) % n_circ
                v0 = 0 * n_circ + j
                v1 = 0 * n_circ + j_next
                faces.append([center_front, v1, v0])  # inward-facing normal

        # Rear face (at contour_x[-1])
        if contour_y[-1] > 1e-10:
            center_rear = len(vertices)
            cx = contour_x[-1]
            vertices = np.vstack([vertices, [[cx, 0.0, 0.0]]])
            last_ring = (n_axial - 1) * n_circ
            for j in range(n_circ):
                j_next = (j + 1) % n_circ
                v0 = last_ring + j
                v1 = last_ring + j_next
                faces.append([center_rear, v0, v1])

    faces_arr = np.array(faces, dtype=int)

    # Compute face normals
    normals = _compute_face_normals(vertices, faces_arr)

    return RevolutionMesh(vertices=vertices, faces=faces_arr, normals=normals)


def _compute_face_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Compute unit normal vectors for each triangular face."""
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]

    edge1 = v1 - v0
    edge2 = v2 - v0
    normals = np.cross(edge1, edge2)

    # Normalise
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms = np.where(norms < 1e-30, 1.0, norms)
    normals = normals / norms

    return normals


def combine_contours(
    chamber_x: np.ndarray,
    chamber_y: np.ndarray,
    nozzle_x: np.ndarray,
    nozzle_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Combine chamber and nozzle contours into a single continuous profile.

    The nozzle contour is expected to start at the throat (x=0) and extend
    downstream.  The chamber contour runs from the injector face to the
    throat.  This function offsets the nozzle so that it starts at the
    chamber throat position and concatenates them.

    Args:
        chamber_x: Chamber axial positions (injector → throat) [m].
        chamber_y: Chamber radii [m].
        nozzle_x: Nozzle axial positions (from throat = 0) [m].
        nozzle_y: Nozzle radii [m].

    Returns:
        (x, y) combined contour from injector face to nozzle exit.
    """
    # Offset nozzle by the last chamber x position
    throat_x = chamber_x[-1]
    nozzle_x_shifted = nozzle_x + throat_x

    # Skip duplicate throat point
    x = np.concatenate([chamber_x, nozzle_x_shifted[1:]])
    y = np.concatenate([chamber_y, nozzle_y[1:]])

    return x, y


def export_stl_binary(mesh: RevolutionMesh, filepath: str) -> None:
    """Export mesh to binary STL format.

    Binary STL format (no external dependencies required):
    - 80-byte header
    - 4-byte uint32 number of triangles
    - For each triangle: 12 floats (normal + 3 vertices) + 2 byte attribute

    Args:
        mesh: RevolutionMesh to export.
        filepath: Output file path (should end in .stl).
    """
    import struct

    n_faces = mesh.n_faces
    header = b"RESA Pro STL export" + b"\0" * (80 - 19)

    with open(filepath, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", n_faces))

        for i in range(n_faces):
            normal = mesh.normals[i]
            v0 = mesh.vertices[mesh.faces[i, 0]]
            v1 = mesh.vertices[mesh.faces[i, 1]]
            v2 = mesh.vertices[mesh.faces[i, 2]]

            f.write(struct.pack("<3f", *normal))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))  # attribute byte count


def export_stl_ascii(mesh: RevolutionMesh, filepath: str, name: str = "engine") -> None:
    """Export mesh to ASCII STL format.

    Args:
        mesh: RevolutionMesh to export.
        filepath: Output file path.
        name: Solid name in the STL file.
    """
    with open(filepath, "w") as f:
        f.write(f"solid {name}\n")

        for i in range(mesh.n_faces):
            n = mesh.normals[i]
            v0 = mesh.vertices[mesh.faces[i, 0]]
            v1 = mesh.vertices[mesh.faces[i, 1]]
            v2 = mesh.vertices[mesh.faces[i, 2]]

            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {v0[0]:.6e} {v0[1]:.6e} {v0[2]:.6e}\n")
            f.write(f"      vertex {v1[0]:.6e} {v1[1]:.6e} {v1[2]:.6e}\n")
            f.write(f"      vertex {v2[0]:.6e} {v2[1]:.6e} {v2[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")

        f.write(f"endsolid {name}\n")
