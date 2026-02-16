"""RESA Pro command-line interface package.

Supports ``python -m resa_pro.cli`` as an alternative to the ``resa`` entry point.
"""

from resa_pro.cli.main import cli, main

__all__ = ["cli", "main"]
