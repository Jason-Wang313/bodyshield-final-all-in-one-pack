from bodyshield.robot import healthcheck, safety_gate


def test_robot_entry_points_refuse_before_confirmation():
    assert healthcheck.main([]) == 2
    assert safety_gate.main(["--check-all"]) == 2

