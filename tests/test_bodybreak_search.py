from bodyshield.bodybreak import find_minimal_breaking_perturbation
from bodyshield.perturbations import Perturbation


def test_bodybreak_finds_simple_break():
    candidates = [Perturbation(), Perturbation({"latency_ms": 100})]
    result = find_minimal_breaking_perturbation(
        None,
        None,
        lambda z: 0.0 if z.active_axes() else 1.0,
        search_space=candidates,
        threshold=0.5,
        budget=2,
        mode="grid",
    )
    assert result.notes == "found_break"
    assert "latency_ms" in result.perturbation.active_axes()
