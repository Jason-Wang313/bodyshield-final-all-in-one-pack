"""Compatibility wrapper for the implemented BodyBreak module."""

from bodyshield.bodybreak_search import (  # noqa: F401
    SearchResult,
    compare_search_modes,
    find_minimal_breaking_perturbation,
    perturbation_cost,
)
from bodyshield.perturbations import Perturbation  # noqa: F401
