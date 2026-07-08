"""EPEC-style effect-preserving stress-test policy factory."""

from bodyshield.policies import default_policies


def get_policy():
    return default_policies()["epec"]

