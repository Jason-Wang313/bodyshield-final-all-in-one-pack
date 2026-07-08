"""Nominal policy factory."""

from bodyshield.policies import default_policies


def get_policy():
    return default_policies()["nominal"]

