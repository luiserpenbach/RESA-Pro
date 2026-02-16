"""Design optimization framework for RESA Pro.

Provides a structured interface for defining design spaces, objective
functions, constraints, and running optimizations using SciPy backends.

Supports:
- Single-objective minimization (Nelder-Mead, Powell, L-BFGS-B, etc.)
- Bounded parameter search with linear/nonlinear constraints
- Multi-objective optimization via weighted-sum and epsilon-constraint methods
- Design-of-experiments (DOE) for sampling the design space
- Sensitivity analysis via one-at-a-time (OAT) perturbation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from scipy.optimize import minimize, differential_evolution

logger = logging.getLogger(__name__)


@dataclass
class DesignVariable:
    """A single design variable with bounds and metadata.

    Args:
        name: Variable name (must match the parameter name in the
              evaluation function).
        lower: Lower bound.
        upper: Upper bound.
        initial: Initial value (midpoint if not provided).
        unit: Physical unit string (for display).
    """

    name: str
    lower: float
    upper: float
    initial: float | None = None
    unit: str = ""

    def __post_init__(self) -> None:
        if self.initial is None:
            self.initial = 0.5 * (self.lower + self.upper)

    @property
    def bounds(self) -> tuple[float, float]:
        return (self.lower, self.upper)

    def normalise(self, value: float) -> float:
        """Normalise to [0, 1]."""
        span = self.upper - self.lower
        return (value - self.lower) / span if span > 0 else 0.0

    def denormalise(self, norm_value: float) -> float:
        """Map [0, 1] back to physical range."""
        return self.lower + norm_value * (self.upper - self.lower)


@dataclass
class Objective:
    """An optimisation objective.

    Args:
        name: Human-readable name.
        key: Key in the result dictionary returned by the evaluation function.
        direction: "minimize" or "maximize".
        weight: Weight for multi-objective weighted-sum formulation.
        target: Optional target value (for target-seeking objectives).
    """

    name: str
    key: str
    direction: str = "minimize"  # "minimize" or "maximize"
    weight: float = 1.0
    target: float | None = None

    @property
    def sign(self) -> float:
        """Returns +1 for minimization, -1 for maximization."""
        return 1.0 if self.direction == "minimize" else -1.0


@dataclass
class Constraint:
    """A design constraint.

    The constraint is satisfied when:
        lower <= value <= upper

    Args:
        name: Human-readable name.
        key: Key in the result dictionary.
        lower: Lower bound (None = no lower bound).
        upper: Upper bound (None = no upper bound).
    """

    name: str
    key: str
    lower: float | None = None
    upper: float | None = None

    def is_satisfied(self, value: float) -> bool:
        if self.lower is not None and value < self.lower:
            return False
        if self.upper is not None and value > self.upper:
            return False
        return True

    def violation(self, value: float) -> float:
        """Return the constraint violation magnitude (0 if satisfied)."""
        v = 0.0
        if self.lower is not None:
            v += max(0.0, self.lower - value)
        if self.upper is not None:
            v += max(0.0, value - self.upper)
        return v


@dataclass
class DesignPoint:
    """A single evaluated design point."""

    variables: dict[str, float] = field(default_factory=dict)
    objectives: dict[str, float] = field(default_factory=dict)
    constraints: dict[str, float] = field(default_factory=dict)
    feasible: bool = True
    raw_result: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of an optimization run."""

    best: DesignPoint | None = None
    all_points: list[DesignPoint] = field(default_factory=list)
    pareto_front: list[DesignPoint] = field(default_factory=list)
    n_evaluations: int = 0
    converged: bool = False
    message: str = ""


# Type alias for the evaluation function
EvalFunction = Callable[[dict[str, float]], dict[str, float]]


class DesignOptimizer:
    """Engine design optimizer.

    Usage::

        opt = DesignOptimizer()
        opt.add_variable(DesignVariable("chamber_pressure", 1e6, 5e6, unit="Pa"))
        opt.add_variable(DesignVariable("mixture_ratio", 2.0, 6.0))
        opt.add_objective(Objective("Isp", "Isp_vac", direction="maximize"))
        opt.add_constraint(Constraint("max_heat_flux", "peak_q", upper=10e6))

        result = opt.optimize(eval_func, method="differential_evolution")

    Args:
        eval_func: Function that takes a dict of variable values and
                   returns a dict of result values (objectives + constraints).
    """

    def __init__(self) -> None:
        self._variables: list[DesignVariable] = []
        self._objectives: list[Objective] = []
        self._constraints: list[Constraint] = []

    def add_variable(self, var: DesignVariable) -> None:
        self._variables.append(var)

    def add_objective(self, obj: Objective) -> None:
        self._objectives.append(obj)

    def add_constraint(self, con: Constraint) -> None:
        self._constraints.append(con)

    @property
    def variables(self) -> list[DesignVariable]:
        return self._variables

    @property
    def objectives(self) -> list[Objective]:
        return self._objectives

    @property
    def constraints(self) -> list[Constraint]:
        return self._constraints

    @property
    def n_variables(self) -> int:
        return len(self._variables)

    def _array_to_dict(self, x: np.ndarray) -> dict[str, float]:
        """Convert optimizer array to named variable dict."""
        return {v.name: float(x[i]) for i, v in enumerate(self._variables)}

    def _dict_to_array(self, d: dict[str, float]) -> np.ndarray:
        """Convert variable dict to optimizer array."""
        return np.array([d[v.name] for v in self._variables])

    def _evaluate_point(
        self, x: np.ndarray, eval_func: EvalFunction
    ) -> tuple[float, DesignPoint]:
        """Evaluate a single design point and compute the scalar cost."""
        var_dict = self._array_to_dict(x)
        raw = eval_func(var_dict)

        # Extract objectives
        obj_values = {}
        cost = 0.0
        for obj in self._objectives:
            val = raw.get(obj.key, 0.0)
            obj_values[obj.name] = val
            if obj.target is not None:
                cost += obj.weight * abs(val - obj.target)
            else:
                cost += obj.weight * obj.sign * val

        # Extract and check constraints
        con_values = {}
        feasible = True
        penalty = 0.0
        for con in self._constraints:
            val = raw.get(con.key, 0.0)
            con_values[con.name] = val
            viol = con.violation(val)
            if viol > 0:
                feasible = False
                penalty += 1e6 * viol  # penalty method

        point = DesignPoint(
            variables=var_dict,
            objectives=obj_values,
            constraints=con_values,
            feasible=feasible,
            raw_result=raw,
        )

        return cost + penalty, point

    def optimize(
        self,
        eval_func: EvalFunction,
        method: str = "nelder-mead",
        max_iter: int = 200,
        tol: float = 1e-6,
        seed: int | None = None,
    ) -> OptimizationResult:
        """Run single-objective optimization.

        Args:
            eval_func: Evaluation function mapping variable dict → result dict.
            method: Optimization method. Supports any ``scipy.optimize.minimize``
                    method plus ``"differential_evolution"`` for global search.
            max_iter: Maximum iterations / generations.
            tol: Convergence tolerance.
            seed: Random seed (for stochastic methods).

        Returns:
            OptimizationResult with best point and history.
        """
        if not self._variables:
            raise ValueError("No design variables defined")
        if not self._objectives:
            raise ValueError("No objectives defined")

        bounds = [v.bounds for v in self._variables]
        x0 = np.array([v.initial for v in self._variables])

        all_points: list[DesignPoint] = []

        def cost_function(x: np.ndarray) -> float:
            cost, point = self._evaluate_point(x, eval_func)
            all_points.append(point)
            return cost

        if method.lower() == "differential_evolution":
            result = differential_evolution(
                cost_function,
                bounds=bounds,
                maxiter=max_iter,
                tol=tol,
                seed=seed,
            )
        else:
            # Build options dict with method-appropriate tolerance key
            opts: dict[str, Any] = {"maxiter": max_iter}
            m = method.lower()
            if m == "nelder-mead":
                opts["xatol"] = tol
                opts["fatol"] = tol
            elif m in ("l-bfgs-b", "tnc", "slsqp", "trust-constr", "bfgs", "cg", "newton-cg"):
                opts["gtol"] = tol
            elif m == "powell":
                opts["ftol"] = tol
            else:
                opts["ftol"] = tol

            bounded_methods = ("l-bfgs-b", "tnc", "slsqp", "trust-constr")
            result = minimize(
                cost_function,
                x0,
                method=method,
                bounds=bounds if m in bounded_methods else None,
                options=opts,
            )

        # Find best feasible point
        feasible_points = [p for p in all_points if p.feasible]
        if feasible_points:
            best_idx = 0
            best_cost = float("inf")
            for i, pt in enumerate(feasible_points):
                c, _ = self._evaluate_point(
                    self._dict_to_array(pt.variables), eval_func
                )
                if c < best_cost:
                    best_cost = c
                    best_idx = i
            best = feasible_points[best_idx]
        elif all_points:
            best = all_points[-1]
        else:
            best = None

        return OptimizationResult(
            best=best,
            all_points=all_points,
            n_evaluations=len(all_points),
            converged=result.success,
            message=result.message if hasattr(result, "message") else "",
        )

    def sensitivity_analysis(
        self,
        eval_func: EvalFunction,
        perturbation: float = 0.05,
        base_point: dict[str, float] | None = None,
    ) -> dict[str, dict[str, float]]:
        """One-at-a-time sensitivity analysis.

        Perturbs each variable by ±perturbation (fraction of range)
        around the base point and computes the change in each objective.

        Args:
            eval_func: Evaluation function.
            perturbation: Fractional perturbation of each variable's range.
            base_point: Base design point. If None, uses variable midpoints.

        Returns:
            Nested dict: ``{variable_name: {objective_name: sensitivity}}``.
            Sensitivity = (Δobjective / Δvariable) normalised by ranges.
        """
        if base_point is None:
            base_point = {v.name: v.initial for v in self._variables}

        base_result = eval_func(base_point)
        sensitivities: dict[str, dict[str, float]] = {}

        for var in self._variables:
            dx = perturbation * (var.upper - var.lower)
            if dx == 0:
                continue

            # Perturb up
            point_up = dict(base_point)
            point_up[var.name] = min(base_point[var.name] + dx, var.upper)
            result_up = eval_func(point_up)

            # Perturb down
            point_dn = dict(base_point)
            point_dn[var.name] = max(base_point[var.name] - dx, var.lower)
            result_dn = eval_func(point_dn)

            actual_dx = point_up[var.name] - point_dn[var.name]
            sens = {}
            for obj in self._objectives:
                val_up = result_up.get(obj.key, 0.0)
                val_dn = result_dn.get(obj.key, 0.0)
                # Normalised sensitivity: (Δf/f_base) / (Δx/x_range)
                f_base = base_result.get(obj.key, 1.0)
                x_range = var.upper - var.lower
                if f_base != 0 and x_range != 0:
                    sens[obj.name] = ((val_up - val_dn) / f_base) / (actual_dx / x_range)
                else:
                    sens[obj.name] = 0.0

            sensitivities[var.name] = sens

        return sensitivities

    def doe_latin_hypercube(
        self,
        eval_func: EvalFunction,
        n_samples: int = 50,
        seed: int | None = None,
    ) -> list[DesignPoint]:
        """Latin Hypercube Sampling of the design space.

        Generates a space-filling DOE and evaluates each point.

        Args:
            eval_func: Evaluation function.
            n_samples: Number of sample points.
            seed: Random seed.

        Returns:
            List of evaluated DesignPoint objects.
        """
        rng = np.random.default_rng(seed)
        n_vars = len(self._variables)

        # Generate LHS matrix
        intervals = np.arange(n_samples)
        lhs = np.zeros((n_samples, n_vars))
        for j in range(n_vars):
            perm = rng.permutation(n_samples)
            lhs[:, j] = (perm + rng.uniform(size=n_samples)) / n_samples

        points: list[DesignPoint] = []
        for i in range(n_samples):
            x = np.array([
                v.denormalise(lhs[i, j])
                for j, v in enumerate(self._variables)
            ])
            _, point = self._evaluate_point(x, eval_func)
            points.append(point)

        return points
