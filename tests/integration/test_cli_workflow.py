"""Integration tests for end-to-end CLI workflows.

Tests the full design pipeline: chamber → nozzle → injector → report.
"""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from resa_pro.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestChamberToNozzlePipeline:
    """Test the chamber → nozzle → report pipeline."""

    def test_chamber_saves_json(self, runner, tmp_dir):
        """Chamber command should produce a valid JSON file."""
        out = os.path.join(tmp_dir, "chamber.json")
        result = runner.invoke(cli, [
            "chamber", "--thrust", "2000", "--pc", "2000000", "-o", out
        ])
        assert result.exit_code == 0, result.output
        assert os.path.exists(out)

        with open(out) as f:
            data = json.load(f)
        assert data["chamber"]["throat_diameter"] > 0
        assert "contour_x" in data["chamber"]
        assert "contour_y" in data["chamber"]

    def test_nozzle_from_chamber_design(self, runner, tmp_dir):
        """Nozzle command should read chamber design and produce output."""
        chamber_out = os.path.join(tmp_dir, "chamber.json")
        nozzle_out = os.path.join(tmp_dir, "nozzle.json")

        # Step 1: chamber
        result = runner.invoke(cli, [
            "chamber", "--thrust", "2000", "--pc", "2000000", "-o", chamber_out
        ])
        assert result.exit_code == 0, result.output

        # Step 2: nozzle
        result = runner.invoke(cli, [
            "nozzle", "--expansion-ratio", "8", "--design", chamber_out, "-o", nozzle_out
        ])
        assert result.exit_code == 0, result.output
        assert os.path.exists(nozzle_out)

        with open(nozzle_out) as f:
            data = json.load(f)
        assert data["nozzle"]["expansion_ratio"] == 8.0
        assert "contour_x" in data["nozzle"]

    def test_injector_from_chamber_design(self, runner, tmp_dir):
        """Injector command should read chamber design and produce output."""
        chamber_out = os.path.join(tmp_dir, "chamber.json")
        injector_out = os.path.join(tmp_dir, "injector.json")

        result = runner.invoke(cli, [
            "chamber", "--thrust", "2000", "--pc", "2000000", "-o", chamber_out
        ])
        assert result.exit_code == 0, result.output

        result = runner.invoke(cli, [
            "injector", "--design", chamber_out, "-o", injector_out
        ])
        assert result.exit_code == 0, result.output
        assert os.path.exists(injector_out)

    def test_report_from_design(self, runner, tmp_dir):
        """Report command should generate a text report from design."""
        chamber_out = os.path.join(tmp_dir, "chamber.json")
        result = runner.invoke(cli, [
            "chamber", "--thrust", "2000", "--pc", "2000000", "-o", chamber_out
        ])
        assert result.exit_code == 0, result.output

        report_out = os.path.join(tmp_dir, "report.txt")
        result = runner.invoke(cli, [
            "report", "--design", chamber_out, "--format", "text", "-o", report_out
        ])
        assert result.exit_code == 0, result.output
        assert os.path.exists(report_out)

        with open(report_out) as f:
            content = f.read()
        assert "OPERATING POINT" in content

    def test_html_report(self, runner, tmp_dir):
        """HTML report should be valid HTML."""
        chamber_out = os.path.join(tmp_dir, "chamber.json")
        result = runner.invoke(cli, [
            "chamber", "--thrust", "2000", "--pc", "2000000", "-o", chamber_out
        ])
        assert result.exit_code == 0

        report_out = os.path.join(tmp_dir, "report.html")
        result = runner.invoke(cli, [
            "report", "--design", chamber_out, "--format", "html", "-o", report_out
        ])
        assert result.exit_code == 0
        with open(report_out) as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content


class TestFeedSystemCLI:
    """Test feed system CLI commands."""

    def test_tank_sizing(self, runner):
        result = runner.invoke(cli, [
            "feed", "tank",
            "--mass", "5", "--density", "789", "--pressure", "3000000",
            "--diameter", "0.15",
        ])
        assert result.exit_code == 0, result.output
        assert "Tank Design" in result.output

    def test_pressurant_blowdown(self, runner):
        result = runner.invoke(cli, [
            "feed", "pressurant",
            "--tank-volume", "10", "--tank-pressure", "2500000",
            "--mode", "blowdown",
        ])
        assert result.exit_code == 0, result.output
        assert "Pressurant System" in result.output

    def test_pressurant_regulated(self, runner):
        result = runner.invoke(cli, [
            "feed", "pressurant",
            "--tank-volume", "10", "--tank-pressure", "2500000",
            "--mode", "regulated",
        ])
        assert result.exit_code == 0, result.output

    def test_pressure_budget(self, runner):
        result = runner.invoke(cli, [
            "feed", "budget",
            "--pc", "2000000", "--injector-dp", "400000",
        ])
        assert result.exit_code == 0, result.output
        assert "Pressure Budget" in result.output


class TestInfoCommands:
    """Test info CLI commands."""

    def test_info_propellants(self, runner):
        result = runner.invoke(cli, ["info", "propellants"])
        assert result.exit_code == 0, result.output
        assert "ethanol" in result.output

    def test_info_materials(self, runner):
        result = runner.invoke(cli, ["info", "materials"])
        assert result.exit_code == 0, result.output


class TestSTLExport:
    """Test STL export CLI command."""

    def test_stl_export(self, runner, tmp_dir):
        """Full pipeline: chamber → nozzle → STL."""
        chamber_out = os.path.join(tmp_dir, "design.json")
        stl_out = os.path.join(tmp_dir, "engine.stl")

        # Create chamber design with contour
        result = runner.invoke(cli, [
            "chamber", "--thrust", "2000", "--pc", "2000000", "-o", chamber_out
        ])
        assert result.exit_code == 0

        # Add nozzle data to same file
        result = runner.invoke(cli, [
            "nozzle", "--expansion-ratio", "8", "--design", chamber_out, "-o", chamber_out
        ])
        assert result.exit_code == 0

        # Export STL
        result = runner.invoke(cli, [
            "export-stl", "--design", chamber_out, "-o", stl_out, "--segments", "16"
        ])
        assert result.exit_code == 0, result.output
        assert os.path.exists(stl_out)
        assert os.path.getsize(stl_out) > 0
