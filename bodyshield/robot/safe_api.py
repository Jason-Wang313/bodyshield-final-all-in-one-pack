"""Bounded safe robot API placeholder.

The methods expose the intended contract and refuse to execute until explicit
hardware readiness is confirmed outside the non-hardware artifact.
"""

from __future__ import annotations

from bodyshield.safe_robot_runner import SafeRobot, SafetyViolation

__all__ = ["SafeRobot", "SafetyViolation"]
