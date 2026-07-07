from bodyshield.perturbations import Perturbation


def test_perturbation_cost_and_axes():
    z = Perturbation({"latency_ms": 50, "action_noise_std": 0.1})
    assert "latency_ms" in z.active_axes()
    assert z.cost() > 0
