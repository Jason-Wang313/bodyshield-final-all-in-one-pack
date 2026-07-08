"""BodyShield repaired policy factory."""

from bodyshield.policies import default_policies


def get_policy():
    return default_policies()["bodyshield"] if "bodyshield" in default_policies() else default_policies()["nominal"]

