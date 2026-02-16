"""Tests for the uncertainty quantification module."""

import pytest
import numpy as np

from resa_pro.optimization.uq import (
    Distribution,
    OutputStatistics,
    UncertainParameter,
    UncertaintyAnalysis,
    UQResult,
)


def _linear_eval(params: dict[str, float]) -> dict[str, float]:
    """Simple linear function: y = 2*x + 3*z."""
    x = params.get("x", 0.0)
    z = params.get("z", 0.0)
    return {"y": 2.0 * x + 3.0 * z, "y2": x ** 2}


class TestUncertainParameter:
    """Test parameter sampling."""

    def test_normal_sampling(self):
        p = UncertainParameter("x", 10.0, Distribution.NORMAL, std=1.0)
        rng = np.random.default_rng(42)
        samples = p.sample(rng, 1000)

        assert len(samples) == 1000
        assert abs(np.mean(samples) - 10.0) < 0.2
        assert abs(np.std(samples) - 1.0) < 0.2

    def test_uniform_sampling(self):
        p = UncertainParameter("x", 5.0, Distribution.UNIFORM, lower=0.0, upper=10.0)
        rng = np.random.default_rng(42)
        samples = p.sample(rng, 1000)

        assert np.all(samples >= 0.0)
        assert np.all(samples <= 10.0)
        assert abs(np.mean(samples) - 5.0) < 0.5

    def test_triangular_sampling(self):
        p = UncertainParameter(
            "x", 5.0, Distribution.TRIANGULAR, lower=0.0, upper=10.0, mode=5.0
        )
        rng = np.random.default_rng(42)
        samples = p.sample(rng, 1000)

        assert np.all(samples >= 0.0)
        assert np.all(samples <= 10.0)

    def test_lognormal_sampling(self):
        p = UncertainParameter("x", 10.0, Distribution.LOGNORMAL, std=2.0)
        rng = np.random.default_rng(42)
        samples = p.sample(rng, 1000)

        assert np.all(samples > 0)  # lognormal is always positive


class TestOutputStatistics:
    """Test statistics computation."""

    def test_from_samples(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        stats = OutputStatistics.from_samples("test", data)

        assert stats.name == "test"
        assert stats.mean == pytest.approx(3.0)
        assert stats.median == pytest.approx(3.0)
        assert stats.min_val == 1.0
        assert stats.max_val == 5.0

    def test_std_computation(self):
        rng = np.random.default_rng(42)
        data = rng.normal(10.0, 2.0, size=10000)
        stats = OutputStatistics.from_samples("test", data)

        assert abs(stats.mean - 10.0) < 0.1
        assert abs(stats.std - 2.0) < 0.1

    def test_confidence_interval(self):
        rng = np.random.default_rng(42)
        data = rng.normal(0.0, 1.0, size=10000)
        stats = OutputStatistics.from_samples("test", data)

        # 95% CI should be approximately [-1.96, 1.96]
        assert stats.ci_95_lower < -1.5
        assert stats.ci_95_upper > 1.5


class TestUncertaintyAnalysis:
    """Test the Monte Carlo UQ engine."""

    def test_basic_run(self):
        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter("x", 5.0, Distribution.NORMAL, std=1.0))
        uq.add_parameter(UncertainParameter("z", 3.0, Distribution.NORMAL, std=0.5))
        uq.add_output("y")

        result = uq.run(_linear_eval, n_samples=500, seed=42)

        assert result.n_samples == 500
        assert "y" in result.output_statistics
        # y = 2*x + 3*z → E[y] = 2*5 + 3*3 = 19
        assert abs(result.output_statistics["y"].mean - 19.0) < 1.0

    def test_variance_propagation(self):
        """Var(y) = 4*Var(x) + 9*Var(z) for y = 2x + 3z independent."""
        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter("x", 5.0, Distribution.NORMAL, std=1.0))
        uq.add_parameter(UncertainParameter("z", 3.0, Distribution.NORMAL, std=0.5))
        uq.add_output("y")

        result = uq.run(_linear_eval, n_samples=5000, seed=42)

        expected_var = 4.0 * 1.0 + 9.0 * 0.25  # = 6.25
        expected_std = np.sqrt(expected_var)  # ~2.5
        assert abs(result.output_statistics["y"].std - expected_std) < 0.3

    def test_sensitivity_indices(self):
        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter("x", 5.0, Distribution.NORMAL, std=1.0))
        uq.add_parameter(UncertainParameter("z", 3.0, Distribution.NORMAL, std=0.5))
        uq.add_output("y")

        result = uq.run(_linear_eval, n_samples=2000, seed=42)

        # Both parameters should have non-zero sensitivity
        assert result.sensitivity_indices["x"]["y"] > 0
        assert result.sensitivity_indices["z"]["y"] > 0

    def test_correlations(self):
        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter("x", 5.0, Distribution.NORMAL, std=1.0))
        uq.add_parameter(UncertainParameter("z", 3.0, Distribution.NORMAL, std=0.5))
        uq.add_output("y")

        result = uq.run(_linear_eval, n_samples=2000, seed=42)

        # x should be positively correlated with y (coefficient 2)
        assert result.correlation_matrix["x"]["y"] > 0.3
        # z should also be positively correlated
        assert result.correlation_matrix["z"]["y"] > 0.3

    def test_failed_samples_counted(self):
        def failing_eval(params):
            if params["x"] > 6.0:
                raise ValueError("out of range")
            return {"y": params["x"]}

        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter("x", 5.0, Distribution.NORMAL, std=2.0))
        uq.add_output("y")

        result = uq.run(failing_eval, n_samples=500, seed=42)

        assert result.n_failed > 0
        assert "y" in result.output_statistics

    def test_reproducibility(self):
        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter("x", 5.0, Distribution.NORMAL, std=1.0))
        uq.add_output("y")

        r1 = uq.run(_linear_eval, n_samples=100, seed=99)
        r2 = uq.run(_linear_eval, n_samples=100, seed=99)

        assert r1.output_statistics["y"].mean == pytest.approx(
            r2.output_statistics["y"].mean
        )

    def test_multiple_outputs(self):
        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter("x", 5.0, Distribution.NORMAL, std=1.0))
        uq.add_parameter(UncertainParameter("z", 3.0, Distribution.NORMAL, std=0.5))
        uq.add_output("y")
        uq.add_output("y2")

        result = uq.run(_linear_eval, n_samples=500, seed=42)

        assert "y" in result.output_statistics
        assert "y2" in result.output_statistics
