"""Bounded robot API stub for future hardware execution."""

from __future__ import annotations


class SafetyViolation(RuntimeError):
    pass


class SafeRobot:
    def __init__(self, config):
        self.config = config

    def safety_check(self):
        raise SafetyViolation("Hardware safety gate is not enabled in the non-hardware phase.")

    def reset_to_home(self):
        raise SafetyViolation("Cannot reset hardware before explicit user safety confirmation.")

    def open_gripper(self):
        raise SafetyViolation("Cannot actuate gripper before explicit user safety confirmation.")

    def close_gripper(self, max_effort=None, timeout_s=2.0):
        raise SafetyViolation("Cannot actuate gripper before explicit user safety confirmation.")

    def move_to_pose(self, x=None, y=None, z=None, roll=0, pitch=0, yaw=0, speed_scale=0.3):
        raise SafetyViolation("Cannot move hardware before explicit user safety confirmation.")

    def move_relative(self, dx, dy, dz, droll=0, dpitch=0, dyaw=0, speed_scale=0.3):
        raise SafetyViolation("Cannot move hardware before explicit user safety confirmation.")

    def attempt_push(self, start_pose, end_pose, speed_scale=0.2):
        raise SafetyViolation("Cannot attempt push before explicit user safety confirmation.")

    def attempt_press(self, target_pose, speed_scale=0.15):
        raise SafetyViolation("Cannot attempt press before explicit user safety confirmation.")

    def attempt_grasp(self, pre_pose, grasp_pose, lift_pose, speed_scale=0.2):
        raise SafetyViolation("Cannot attempt grasp before explicit user safety confirmation.")

    def attempt_pull(self, contact_pose, pull_vector, speed_scale=0.15):
        raise SafetyViolation("Cannot attempt pull before explicit user safety confirmation.")

    def stop_now(self):
        raise SafetyViolation("No hardware controller is active.")


def run_batch(config_path: str):
    raise SafetyViolation(f"Refusing hardware batch for {config_path}: safety gate not confirmed.")
