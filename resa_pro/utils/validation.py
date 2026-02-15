"""Design rule checking and input validation for RESA Pro."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    """Severity level for validation messages."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationMessage:
    """A single validation finding."""

    severity: Severity
    parameter: str
    message: str
    value: Any = None
    limit: Any = None


@dataclass
class ValidationResult:
    """Aggregated validation result."""

    messages: list[ValidationMessage] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(m.severity == Severity.ERROR for m in self.messages)

    @property
    def has_warnings(self) -> bool:
        return any(m.severity == Severity.WARNING for m in self.messages)

    @property
    def errors(self) -> list[ValidationMessage]:
        return [m for m in self.messages if m.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationMessage]:
        return [m for m in self.messages if m.severity == Severity.WARNING]

    def add(self, severity: Severity, parameter: str, message: str, **kwargs: Any) -> None:
        self.messages.append(
            ValidationMessage(severity=severity, parameter=parameter, message=message, **kwargs)
        )

    def error(self, parameter: str, message: str, **kwargs: Any) -> None:
        self.add(Severity.ERROR, parameter, message, **kwargs)

    def warning(self, parameter: str, message: str, **kwargs: Any) -> None:
        self.add(Severity.WARNING, parameter, message, **kwargs)

    def info(self, parameter: str, message: str, **kwargs: Any) -> None:
        self.add(Severity.INFO, parameter, message, **kwargs)

    def merge(self, other: ValidationResult) -> None:
        self.messages.extend(other.messages)


# --- Common validators ---


def validate_positive(name: str, value: float, result: ValidationResult) -> None:
    """Validate that a value is strictly positive."""
    if value <= 0:
        result.error(name, f"{name} must be positive, got {value}")


def validate_range(
    name: str,
    value: float,
    low: float,
    high: float,
    result: ValidationResult,
    severity: Severity = Severity.ERROR,
) -> None:
    """Validate that a value falls within [low, high]."""
    if value < low or value > high:
        result.add(severity, name, f"{name} = {value} is outside [{low}, {high}]")


def validate_chamber_design(design: dict) -> ValidationResult:
    """Run validation checks on a chamber design dictionary.

    Checks physical reasonableness of chamber parameters.
    """
    result = ValidationResult()

    pc = design.get("chamber_pressure")
    if pc is not None:
        validate_positive("chamber_pressure", pc, result)
        if pc > 30e6:
            result.warning(
                "chamber_pressure",
                f"Chamber pressure {pc / 1e6:.1f} MPa is very high",
            )

    thrust = design.get("thrust")
    if thrust is not None:
        validate_positive("thrust", thrust, result)

    dt = design.get("throat_diameter")
    if dt is not None:
        validate_positive("throat_diameter", dt, result)
        if dt < 1e-3:
            result.warning("throat_diameter", f"Throat diameter {dt * 1e3:.2f} mm is very small")

    cr = design.get("contraction_ratio")
    if cr is not None:
        if cr < 1.0:
            result.error("contraction_ratio", "Contraction ratio must be >= 1.0")
        if cr > 10.0:
            result.warning("contraction_ratio", f"Contraction ratio {cr:.1f} is unusually high")

    l_star = design.get("l_star")
    if l_star is not None:
        validate_positive("l_star", l_star, result)
        validate_range("l_star", l_star, 0.2, 5.0, result, Severity.WARNING)

    eps = design.get("expansion_ratio")
    if eps is not None:
        if eps < 1.0:
            result.error("expansion_ratio", "Expansion ratio must be >= 1.0")
        if eps > 300:
            result.warning("expansion_ratio", f"Expansion ratio {eps:.0f} is very large")

    return result
