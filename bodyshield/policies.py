"""Policy parameterizations used by the non-hardware simulator."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .perturbations import AXES


BASE_SENSITIVITY = {
    "latency_ms": 0.95,
    "action_noise_std": 1.05,
    "joint_range_scale": 0.90,
    "joint_lock": 1.65,
    "gripper_limit_scale": 0.85,
    "speed_cap_scale": 0.70,
    "acceleration_cap_scale": 0.78,
    "calibration_offset_mm": 1.00,
    "camera_shift_px": 0.70,
    "controller_rate_scale": 0.88,
    "payload_g": 0.55,
    "tool_extension_cm": 0.55,
    "physical_gripper_restriction_mm": 0.95,
    "obstacle_clearance_cm": 1.05,
    "friction_surface": 0.85,
}


@dataclass(frozen=True)
class Policy:
    method_id: str
    display_name: str
    base_success: float
    sensitivity: dict[str, float]
    nominal_penalty: float = 0.0
    time_scale: float = 1.0
    repair_axes: dict[str, float] | None = None

    def with_id(self, method_id: str, display_name: str | None = None) -> "Policy":
        return replace(self, method_id=method_id, display_name=display_name or method_id)


def scaled_sensitivity(scale: float, overrides: dict[str, float] | None = None) -> dict[str, float]:
    values = {axis: BASE_SENSITIVITY.get(axis, 1.0) * scale for axis in AXES}
    for axis, value in (overrides or {}).items():
        values[axis] = value
    return values


def default_policies() -> dict[str, Policy]:
    """Return required baselines with deliberately distinct failure modes."""

    policies = {
        "nominal": Policy(
            "nominal",
            "Nominal",
            0.925,
            scaled_sensitivity(1.00),
            time_scale=1.00,
        ),
        "domain_randomization": Policy(
            "domain_randomization",
            "Domain randomization",
            0.905,
            scaled_sensitivity(
                0.72,
                {
                    "payload_g": 0.48,
                    "tool_extension_cm": 0.48,
                    "friction_surface": 0.62,
                    "physical_gripper_restriction_mm": 0.78,
                    "obstacle_clearance_cm": 0.86,
                },
            ),
            nominal_penalty=0.010,
            time_scale=1.05,
        ),
        "random_tuning": Policy(
            "random_tuning",
            "Random perturbation tuning",
            0.895,
            scaled_sensitivity(
                0.80,
                {
                    "latency_ms": 0.72,
                    "action_noise_std": 0.76,
                    "calibration_offset_mm": 0.74,
                    "controller_rate_scale": 0.76,
                    "payload_g": 0.70,
                    "tool_extension_cm": 0.70,
                },
            ),
            nominal_penalty=0.012,
            time_scale=1.08,
        ),
        "grid_worstcase": Policy(
            "grid_worstcase",
            "Worst-case grid tuning",
            0.890,
            scaled_sensitivity(
                0.68,
                {
                    "latency_ms": 0.52,
                    "action_noise_std": 0.62,
                    "calibration_offset_mm": 0.58,
                    "controller_rate_scale": 0.56,
                    "acceleration_cap_scale": 0.52,
                    "payload_g": 0.62,
                    "tool_extension_cm": 0.66,
                },
            ),
            nominal_penalty=0.015,
            time_scale=1.12,
        ),
        "robust_control": Policy(
            "robust_control",
            "Robust control",
            0.875,
            scaled_sensitivity(
                0.58,
                {
                    "speed_cap_scale": 0.34,
                    "acceleration_cap_scale": 0.38,
                    "controller_rate_scale": 0.50,
                    "joint_range_scale": 0.48,
                    "joint_lock": 1.15,
                    "camera_shift_px": 0.60,
                },
            ),
            nominal_penalty=0.025,
            time_scale=1.35,
        ),
        "sysid_retune": Policy(
            "sysid_retune",
            "SysID + retune",
            0.900,
            scaled_sensitivity(
                0.74,
                {
                    "calibration_offset_mm": 0.38,
                    "speed_cap_scale": 0.46,
                    "acceleration_cap_scale": 0.50,
                    "controller_rate_scale": 0.44,
                    "latency_ms": 0.55,
                    "payload_g": 0.82,
                    "tool_extension_cm": 0.80,
                    "friction_surface": 0.78,
                },
            ),
            nominal_penalty=0.008,
            time_scale=1.10,
        ),
        "oracle": Policy(
            "oracle",
            "Oracle feasibility",
            0.985,
            scaled_sensitivity(0.20, {"joint_lock": 0.55}),
            nominal_penalty=0.005,
            time_scale=1.20,
        ),
        "human_effect_prior": Policy(
            "human_effect_prior",
            "Human/effect prior",
            0.915,
            scaled_sensitivity(
                1.08,
                {
                    "camera_shift_px": 0.52,
                    "payload_g": 0.82,
                    "tool_extension_cm": 0.72,
                    "physical_gripper_restriction_mm": 1.05,
                    "obstacle_clearance_cm": 1.02,
                    "calibration_offset_mm": 1.18,
                    "latency_ms": 1.20,
                    "controller_rate_scale": 1.08,
                },
            ),
            time_scale=0.96,
        ),
        "epec": Policy(
            "epec",
            "EPEC alternatives",
            0.905,
            scaled_sensitivity(
                0.88,
                {
                    "gripper_limit_scale": 0.46,
                    "tool_extension_cm": 0.42,
                    "payload_g": 0.46,
                    "physical_gripper_restriction_mm": 0.44,
                    "friction_surface": 0.55,
                    "latency_ms": 1.08,
                    "action_noise_std": 1.02,
                    "controller_rate_scale": 0.92,
                },
            ),
            nominal_penalty=0.008,
            time_scale=1.18,
        ),
    }
    return policies
