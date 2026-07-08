"""SysID-plus-retune baseline policy factory."""

from bodyshield.policies import default_policies


def get_policy():
    return default_policies()["sysid_retune"]

