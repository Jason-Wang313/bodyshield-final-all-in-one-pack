from bodyshield.core.bodybreak import find_minimal_breaking_perturbation


def test_bodybreak_core_wrapper_finds_or_returns_candidate():
    result = find_minimal_breaking_perturbation(
        policy=None,
        task=None,
        evaluator=lambda z: 0.0 if z.cost() > 0.2 else 1.0,
        threshold=0.5,
        budget=20,
        mode="one_axis",
        seed=1,
    )
    assert result.trials > 0
    assert result.perturbation.cost() >= 0.0

