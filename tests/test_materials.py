"""Tests for the materials module."""

import pytest

from resa_pro.core.materials import Material, get_material_info, list_materials


class TestMaterialsDatabase:
    def test_list_materials(self):
        mats = list_materials()
        assert len(mats) > 0
        assert "copper_c10100" in mats

    def test_get_material_info(self):
        info = get_material_info("copper_c10100")
        assert info["name"] == "C10100 OFE Copper"
        assert info["density"] > 0

    def test_missing_material(self):
        with pytest.raises(KeyError):
            get_material_info("unobtanium")


class TestMaterialClass:
    def test_copper_conductivity(self):
        mat = Material("copper_c10100")
        k = mat.thermal_conductivity(293)
        assert 350 < k < 400  # ~391 W/(m·K)

    def test_copper_specific_heat(self):
        mat = Material("copper_c10100")
        cp = mat.specific_heat(293)
        assert 370 < cp < 400  # ~385 J/(kg·K)

    def test_thermal_diffusivity(self):
        mat = Material("copper_c10100")
        alpha = mat.thermal_diffusivity(293)
        assert alpha > 0

    def test_ss316(self):
        mat = Material("ss316")
        assert mat.density == pytest.approx(7990)
        k = mat.thermal_conductivity(293)
        assert 12 < k < 15  # ~13.4 W/(m·K)

    def test_repr(self):
        mat = Material("inconel_718")
        assert "Inconel 718" in repr(mat)
