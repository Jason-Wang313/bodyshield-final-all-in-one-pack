"""Policy package required by the v2 submission-grade layout."""

from __future__ import annotations

from bodyshield._legacy import load_legacy_module

_legacy = load_legacy_module("policies", "policies.py")

Policy = _legacy.Policy
BASE_SENSITIVITY = _legacy.BASE_SENSITIVITY
scaled_sensitivity = _legacy.scaled_sensitivity
default_policies = _legacy.default_policies

__all__ = ["Policy", "BASE_SENSITIVITY", "scaled_sensitivity", "default_policies"]

