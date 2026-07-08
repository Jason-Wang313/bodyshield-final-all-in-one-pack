"""Domain-randomization baseline policy factory."""

from bodyshield.policies import default_policies


def get_policy():
    return default_policies()["domain_randomization"]

