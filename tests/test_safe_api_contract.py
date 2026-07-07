import pytest

from bodyshield.robot.safe_api import SafeRobot, SafetyViolation


def test_safe_api_refuses_without_confirmation():
    robot = SafeRobot(config={})
    with pytest.raises(SafetyViolation):
        robot.reset_to_home()
