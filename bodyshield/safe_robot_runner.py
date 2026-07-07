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

    def move_to_pose(self, pose, speed_scale=0.2):
        raise SafetyViolation("Cannot move hardware before explicit user safety confirmation.")

    def stop_now(self):
        raise SafetyViolation("No hardware controller is active.")


def run_batch(config_path: str):
    raise SafetyViolation(f"Refusing hardware batch for {config_path}: safety gate not confirmed.")
