"""Tests for the optimisation framework."""

import pytest
import numpy as np

from resa_pro.optimization.optimizer import (
    Constraint,
    DesignOptimizer,
    DesignPoint,
    DesignVariable,
    Objective,
    OptimizationResult,
)


def _quadratic_eval(params: dict[str, float]) -> dict[str, float]:
    """Simple quadratic test function: f = (x-3)^2 + (y-2)^2."""
    x = params.get("x", 0.0)
    y = params.get("y", 0.0)
    return {
        "f": (x - 3.0) ** 2 + (y - 2.0) ** 2,
        "x_val": x,
        "y_val": y,
    }


def _rosenbrock_eval(params: dict[str, float]) -> dict[str, float]:
    """Rosenbrock function: f = (1-x)^2 + 100*(y-x^2)^2."""
    x = params.get("x", 0.0)
    y = params.get("y", 0.0)
    return {
        "f": (1 - x) ** 2 + 100 * (y - x ** 2) ** 2,
    }


class TestDesignVariable:
    """Test DesignVariable."""

    def test_bounds(self):
        v = DesignVariable("x", 1.0, 10.0)
        assert v.bounds == (1.0, 10.0)

    def test_default_initial(self):
        v = DesignVariable("x", 0.0, 10.0)
        assert v.initial == 5.0

    def test_normalise(self):
        v = DesignVariable("x", 0.0, 10.0)
        assert v.normalise(5.0) == pytest.approx(0.5)
        assert v.normalise(0.0) == pytest.approx(0.0)
        assert v.normalise(10.0) == pytest.approx(1.0)

    def test_denormalise(self):
        v = DesignVariable("x", 0.0, 10.0)
        assert v.denormalise(0.5) == pytest.approx(5.0)


class TestObjective:
    """Test Objective."""

    def test_minimize_sign(self):
        obj = Objective("f", "f", direction="minimize")
        assert obj.sign == 1.0

    def test_maximize_sign(self):
        obj = Objective("f", "f", direction="maximize")
        assert obj.sign == -1.0


class TestConstraint:
    """Test Constraint."""

    def test_satisfied(self):
        c = Constraint("c", "val", lower=0.0, upper=10.0)
        assert c.is_satisfied(5.0) is True
        assert c.is_satisfied(-1.0) is False
        assert c.is_satisfied(11.0) is False

    def test_violation(self):
        c = Constraint("c", "val", lower=0.0, upper=10.0)
        assert c.violation(5.0) == 0.0
        assert c.violation(-2.0) == pytest.approx(2.0)
        assert c.violation(13.0) == pytest.approx(3.0)


class TestDesignOptimizer:
    """Test the optimiser."""

    def test_quadratic_nelder_mead(self):
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", -10.0, 10.0))
        opt.add_variable(DesignVariable("y", -10.0, 10.0))
        opt.add_objective(Objective("f", "f", direction="minimize"))

        result = opt.optimize(_quadratic_eval, method="nelder-mead", max_iter=200)

        assert result.best is not None
        assert result.best.variables["x"] == pytest.approx(3.0, abs=0.1)
        assert result.best.variables["y"] == pytest.approx(2.0, abs=0.1)

    def test_differential_evolution(self):
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", -10.0, 10.0))
        opt.add_variable(DesignVariable("y", -10.0, 10.0))
        opt.add_objective(Objective("f", "f", direction="minimize"))

        result = opt.optimize(
            _quadratic_eval, method="differential_evolution", max_iter=50, seed=42
        )

        assert result.best is not None
        assert result.best.objectives["f"] < 0.5

    def test_maximization(self):
        """Maximize -f is equivalent to minimizing f."""
        def neg_eval(params):
            r = _quadratic_eval(params)
            r["neg_f"] = -r["f"]
            return r

        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", -10.0, 10.0))
        opt.add_variable(DesignVariable("y", -10.0, 10.0))
        opt.add_objective(Objective("neg_f", "neg_f", direction="maximize"))

        result = opt.optimize(neg_eval, method="nelder-mead", max_iter=200)

        assert result.best is not None
        assert result.best.variables["x"] == pytest.approx(3.0, abs=0.5)

    def test_with_constraint(self):
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", -10.0, 10.0))
        opt.add_variable(DesignVariable("y", -10.0, 10.0))
        opt.add_objective(Objective("f", "f", direction="minimize"))
        opt.add_constraint(Constraint("x_positive", "x_val", lower=0.0))

        result = opt.optimize(_quadratic_eval, method="nelder-mead", max_iter=200)

        assert result.best is not None
        assert result.best.feasible is True

    def test_no_variables_raises(self):
        opt = DesignOptimizer()
        opt.add_objective(Objective("f", "f"))
        with pytest.raises(ValueError, match="No design variables"):
            opt.optimize(_quadratic_eval)

    def test_no_objectives_raises(self):
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", 0, 10))
        with pytest.raises(ValueError, match="No objectives"):
            opt.optimize(_quadratic_eval)


class TestSensitivityAnalysis:
    """Test sensitivity analysis."""

    def test_sensitivity_quadratic(self):
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", -10.0, 10.0, initial=3.0))
        opt.add_variable(DesignVariable("y", -10.0, 10.0, initial=2.0))
        opt.add_objective(Objective("f", "f"))

        sens = opt.sensitivity_analysis(_quadratic_eval)

        assert "x" in sens
        assert "y" in sens
        assert "f" in sens["x"]

    def test_sensitivity_at_optimum(self):
        """At the optimum, sensitivities should be near zero."""
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", -10.0, 10.0, initial=3.0))
        opt.add_variable(DesignVariable("y", -10.0, 10.0, initial=2.0))
        opt.add_objective(Objective("f", "f"))

        sens = opt.sensitivity_analysis(
            _quadratic_eval,
            base_point={"x": 3.0, "y": 2.0},
        )

        # Near optimum, derivatives are small
        assert abs(sens["x"]["f"]) < 0.5
        assert abs(sens["y"]["f"]) < 0.5


class TestDOE:
    """Test design of experiments."""

    def test_lhs_sampling(self):
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", 0.0, 10.0))
        opt.add_variable(DesignVariable("y", 0.0, 10.0))
        opt.add_objective(Objective("f", "f"))

        points = opt.doe_latin_hypercube(_quadratic_eval, n_samples=20, seed=42)

        assert len(points) == 20
        assert all(isinstance(p, DesignPoint) for p in points)
        # All points should be within bounds
        for p in points:
            assert 0.0 <= p.variables["x"] <= 10.0
            assert 0.0 <= p.variables["y"] <= 10.0

    def test_lhs_reproducible(self):
        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("x", 0.0, 10.0))
        opt.add_objective(Objective("f", "f"))

        pts1 = opt.doe_latin_hypercube(_quadratic_eval, n_samples=10, seed=123)
        pts2 = opt.doe_latin_hypercube(_quadratic_eval, n_samples=10, seed=123)

        for p1, p2 in zip(pts1, pts2):
            assert p1.variables["x"] == pytest.approx(p2.variables["x"])
