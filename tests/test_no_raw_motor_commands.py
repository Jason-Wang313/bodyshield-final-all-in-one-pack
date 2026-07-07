from pathlib import Path


def test_no_forbidden_raw_motor_tokens_in_robot_package():
    forbidden = ["serial.Serial(", "write_goal_position(", "set_servo_angle(", "movej(", "movel("]
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in Path("bodyshield/robot").glob("*.py"))
    assert not [token for token in forbidden if token in text]
