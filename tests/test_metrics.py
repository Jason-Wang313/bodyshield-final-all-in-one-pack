from bodyshield.metrics import retention, success_interval, success_rate


def test_metrics_basic():
    assert success_rate([1, 0, True]) == 2 / 3
    low, high = success_interval(5, 10)
    assert 0 <= low <= high <= 1
    assert retention(0.8, 1.0) == 0.8
