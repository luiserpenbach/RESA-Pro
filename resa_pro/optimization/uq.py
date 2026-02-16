"""Uncertainty quantification (UQ) for RESA Pro.

Provides Monte Carlo simulation, parameter uncertainty propagation,
and variance-based sensitivity indices for engine design analysis.

Supports:
- Monte Carlo propagation with normal, uniform, and triangular distributions
- Statistical summary (mean, std, percentiles, confidence intervals)
- First-order sensitivity indices (variance-based, Sobol-like)
- Correlation analysis between inputs and outputs
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)

EvalFunction = Callable[[dict[str, float]], dict[str, float]]


class Distribution(Enum):
    """Supported probability distributions for uncertain parameters."""

    NORMAL = "normal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"


@dataclass
class UncertainParameter:
    """An uncertain input parameter.

    Args:
        name: Parameter name (must match eval function keys).
        nominal: Nominal (best-estimate) value.
        distribution: Probability distribution type.
        std: Standard deviation (for normal/lognormal).
        lower: Lower bound (for uniform/triangular).
        upper: Upper bound (for uniform/triangular).
        mode: Mode value (for triangular distribution).
        unit: Physical unit string (for display).
    """

    name: str
    nominal: float
    distribution: Distribution = Distribution.NORMAL
    std: float = 0.0
    lower: float = 0.0
    upper: float = 0.0
    mode: float | None = None
    unit: str = ""

    def sample(self, rng: np.random.Generator, n: int) -> np.ndarray:
        """Generate n samples from this parameter's distribution."""
        if self.distribution == Distribution.NORMAL:
            return rng.normal(self.nominal, self.std, size=n)
        elif self.distribution == Distribution.UNIFORM:
            return rng.uniform(self.lower, self.upper, size=n)
        elif self.distribution == Distribution.TRIANGULAR:
            mode = self.mode if self.mode is not None else self.nominal
            return rng.triangular(self.lower, mode, self.upper, size=n)
        elif self.distribution == Distribution.LOGNORMAL:
            # Convert to lognormal parameters
            mu = np.log(self.nominal**2 / np.sqrt(self.std**2 + self.nominal**2))
            sigma = np.sqrt(np.log(1 + (self.std / self.nominal) ** 2))
            return rng.lognormal(mu, sigma, size=n)
        else:
            raise ValueError(f"Unknown distribution: {self.distribution}")


@dataclass
class OutputStatistics:
    """Statistical summary of a single output quantity."""

    name: str
    mean: float = 0.0
    std: float = 0.0
    median: float = 0.0
    p05: float = 0.0  # 5th percentile
    p25: float = 0.0  # 25th percentile
    p75: float = 0.0  # 75th percentile
    p95: float = 0.0  # 95th percentile
    min_val: float = 0.0
    max_val: float = 0.0
    ci_95_lower: float = 0.0  # 95% confidence interval lower
    ci_95_upper: float = 0.0  # 95% confidence interval upper
    samples: np.ndarray = field(default_factory=lambda: np.array([]))

    @classmethod
    def from_samples(cls, name: str, data: np.ndarray) -> OutputStatistics:
        """Compute statistics from a sample array."""
        return cls(
            name=name,
            mean=float(np.mean(data)),
            std=float(np.std(data, ddof=1)) if len(data) > 1 else 0.0,
            median=float(np.median(data)),
            p05=float(np.percentile(data, 5)),
            p25=float(np.percentile(data, 25)),
            p75=float(np.percentile(data, 75)),
            p95=float(np.percentile(data, 95)),
            min_val=float(np.min(data)),
            max_val=float(np.max(data)),
            ci_95_lower=float(np.percentile(data, 2.5)),
            ci_95_upper=float(np.percentile(data, 97.5)),
            samples=data,
        )


@dataclass
class UQResult:
    """Complete uncertainty quantification result."""

    n_samples: int = 0
    input_parameters: list[UncertainParameter] = field(default_factory=list)
    output_statistics: dict[str, OutputStatistics] = field(default_factory=dict)
    sensitivity_indices: dict[str, dict[str, float]] = field(default_factory=dict)
    correlation_matrix: dict[str, dict[str, float]] = field(default_factory=dict)
    n_failed: int = 0


class UncertaintyAnalysis:
    """Monte Carlo uncertainty quantification engine.

    Usage::

        uq = UncertaintyAnalysis()
        uq.add_parameter(UncertainParameter(
            "chamber_pressure", 2e6, Distribution.NORMAL, std=0.1e6
        ))
        uq.add_parameter(UncertainParameter(
            "mixture_ratio", 4.0, Distribution.UNIFORM, lower=3.5, upper=4.5
        ))
        uq.add_output("Isp_vac")
        uq.add_output("c_star")

        result = uq.run(eval_func, n_samples=1000)
    """

    def __init__(self) -> None:
        self._parameters: list[UncertainParameter] = []
        self._output_keys: list[str] = []

    def add_parameter(self, param: UncertainParameter) -> None:
        self._parameters.append(param)

    def add_output(self, key: str) -> None:
        self._output_keys.append(key)

    @property
    def parameters(self) -> list[UncertainParameter]:
        return self._parameters

    @property
    def output_keys(self) -> list[str]:
        return self._output_keys

    def run(
        self,
        eval_func: EvalFunction,
        n_samples: int = 1000,
        seed: int | None = None,
    ) -> UQResult:
        """Run Monte Carlo uncertainty propagation.

        Args:
            eval_func: Function mapping parameter dict → output dict.
            n_samples: Number of Monte Carlo samples.
            seed: Random seed for reproducibility.

        Returns:
            UQResult with statistics, sensitivity indices, and correlations.
        """
        rng = np.random.default_rng(seed)

        # Generate input samples
        input_samples: dict[str, np.ndarray] = {}
        for param in self._parameters:
            input_samples[param.name] = param.sample(rng, n_samples)

        # Evaluate all samples
        output_samples: dict[str, list[float]] = {key: [] for key in self._output_keys}
        n_failed = 0

        for i in range(n_samples):
            params = {}
            for param in self._parameters:
                params[param.name] = float(input_samples[param.name][i])

            try:
                result = eval_func(params)
                for key in self._output_keys:
                    output_samples[key].append(result.get(key, 0.0))
            except Exception as e:
                n_failed += 1
                logger.debug("Sample %d failed: %s", i, e)
                for key in self._output_keys:
                    output_samples[key].append(np.nan)

        # Compute statistics
        stats: dict[str, OutputStatistics] = {}
        for key in self._output_keys:
            data = np.array(output_samples[key])
            valid = data[~np.isnan(data)]
            if len(valid) > 0:
                stats[key] = OutputStatistics.from_samples(key, valid)

        # Compute sensitivity indices (variance-based, first-order)
        sensitivity = self._compute_sensitivity_indices(
            input_samples, output_samples, n_samples
        )

        # Compute correlations
        correlations = self._compute_correlations(input_samples, output_samples)

        return UQResult(
            n_samples=n_samples,
            input_parameters=self._parameters,
            output_statistics=stats,
            sensitivity_indices=sensitivity,
            correlation_matrix=correlations,
            n_failed=n_failed,
        )

    def _compute_sensitivity_indices(
        self,
        input_samples: dict[str, np.ndarray],
        output_samples: dict[str, list[float]],
        n_samples: int,
    ) -> dict[str, dict[str, float]]:
        """Estimate first-order sensitivity indices.

        Uses a binning approach: for each input, partition samples into
        bins and compute the variance of bin means relative to total
        variance. This approximates the Sobol first-order index:
            S_i ≈ Var(E[Y|X_i]) / Var(Y)
        """
        sensitivity: dict[str, dict[str, float]] = {}
        n_bins = max(10, n_samples // 50)

        for param in self._parameters:
            x = input_samples[param.name]
            param_sens: dict[str, float] = {}

            for key in self._output_keys:
                y = np.array(output_samples[key])
                valid = ~np.isnan(y)
                if valid.sum() < n_bins:
                    param_sens[key] = 0.0
                    continue

                x_valid = x[valid]
                y_valid = y[valid]
                total_var = np.var(y_valid)

                if total_var == 0:
                    param_sens[key] = 0.0
                    continue

                # Bin the input and compute conditional means
                bin_edges = np.linspace(x_valid.min(), x_valid.max(), n_bins + 1)
                bin_indices = np.digitize(x_valid, bin_edges) - 1
                bin_indices = np.clip(bin_indices, 0, n_bins - 1)

                bin_means = np.zeros(n_bins)
                for b in range(n_bins):
                    mask = bin_indices == b
                    if mask.sum() > 0:
                        bin_means[b] = np.mean(y_valid[mask])
                    else:
                        bin_means[b] = np.mean(y_valid)

                var_of_means = np.var(bin_means)
                param_sens[key] = float(var_of_means / total_var)

            sensitivity[param.name] = param_sens

        return sensitivity

    def _compute_correlations(
        self,
        input_samples: dict[str, np.ndarray],
        output_samples: dict[str, list[float]],
    ) -> dict[str, dict[str, float]]:
        """Compute Pearson correlation between inputs and outputs."""
        correlations: dict[str, dict[str, float]] = {}

        for param in self._parameters:
            x = input_samples[param.name]
            corr_row: dict[str, float] = {}

            for key in self._output_keys:
                y = np.array(output_samples[key])
                valid = ~np.isnan(y)
                if valid.sum() < 3:
                    corr_row[key] = 0.0
                    continue
                corr_matrix = np.corrcoef(x[valid], y[valid])
                corr_row[key] = float(corr_matrix[0, 1])

            correlations[param.name] = corr_row

        return correlations
