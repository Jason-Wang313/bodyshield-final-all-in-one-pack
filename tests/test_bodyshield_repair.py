from bodyshield.bodyshield import repair_policy
from bodyshield.perturbations import Perturbation
from bodyshield.policies import default_policies


def test_bodyshield_repair_returns_bodyshield_policy():
    policy = default_policies()["nominal"]
    result = repair_policy(
        policy,
        [{"perturbation": Perturbation({"latency_ms": 100}), "success_rate": 0.2}],
        budget=8,
        seed=1,
    )
    assert result.policy.method_id == "bodyshield"
    assert result.axis_importance["latency_ms"] > 0
