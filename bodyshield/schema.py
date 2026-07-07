"""Validation for the unified trial schema."""

from __future__ import annotations

from typing import Any


REQUIRED_TOP_LEVEL = {
    "trial_id",
    "timestamp",
    "phase",
    "task_id",
    "robot_id",
    "policy_id",
    "method_id",
    "perturbation",
    "initial_state",
    "action_trace_path",
    "verifier",
    "human_audit",
    "safety",
    "result",
    "metadata",
}

REQUIRED_PERTURBATION = {
    "latency_ms",
    "action_noise_std",
    "joint_range_scale",
    "joint_lock",
    "gripper_limit_scale",
    "speed_cap_scale",
    "acceleration_cap_scale",
    "calibration_offset_mm",
    "camera_shift_px",
    "controller_rate_scale",
    "payload_g",
    "tool_extension_cm",
    "physical_gripper_restriction_mm",
    "obstacle_clearance_cm",
    "friction_surface",
}

METHOD_IDS = {
    "nominal",
    "random_tuning",
    "domain_randomization",
    "grid_worstcase",
    "robust_control",
    "sysid_retune",
    "oracle",
    "human_effect_prior",
    "epec",
    "bodyshield",
}

TRIAL_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "BodyShieldTrial",
    "type": "object",
    "required": sorted(REQUIRED_TOP_LEVEL),
    "additionalProperties": True,
    "properties": {
        "trial_id": {"type": "string"},
        "timestamp": {"type": "string"},
        "phase": {"enum": ["simulation", "hardware"]},
        "task_id": {"type": "string"},
        "robot_id": {"type": "string"},
        "policy_id": {"type": "string"},
        "method_id": {"enum": sorted(METHOD_IDS)},
        "perturbation": {
            "type": "object",
            "required": sorted(REQUIRED_PERTURBATION),
            "additionalProperties": True,
            "properties": {
                "latency_ms": {"type": "number"},
                "action_noise_std": {"type": "number"},
                "joint_range_scale": {"type": "number"},
                "joint_lock": {"type": ["string", "null"]},
                "gripper_limit_scale": {"type": "number"},
                "speed_cap_scale": {"type": "number"},
                "acceleration_cap_scale": {"type": "number"},
                "calibration_offset_mm": {"type": "number"},
                "camera_shift_px": {"type": "number"},
                "controller_rate_scale": {"type": "number"},
                "payload_g": {"type": "number"},
                "tool_extension_cm": {"type": "number"},
                "physical_gripper_restriction_mm": {"type": "number"},
                "obstacle_clearance_cm": {"type": "number"},
                "friction_surface": {"type": ["string", "null"]},
            },
        },
        "initial_state": {"type": "object"},
        "action_trace_path": {"type": "string"},
        "joint_log_path": {"type": ["string", "null"]},
        "video_path": {"type": ["string", "null"]},
        "verifier": {
            "type": "object",
            "required": ["label", "confidence", "raw_measurement", "verifier_version"],
            "properties": {
                "label": {"enum": ["success", "failure", "uncertain"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "raw_measurement": {"type": "object"},
                "verifier_version": {"type": "string"},
            },
        },
        "human_audit": {"type": "object"},
        "safety": {
            "type": "object",
            "required": ["stop_triggered", "workspace_violation"],
            "properties": {
                "stop_triggered": {"type": "boolean"},
                "stop_reason": {"type": ["string", "null"]},
                "max_tracking_error": {"type": ["number", "null"]},
                "max_current_or_load": {"type": ["number", "null"]},
                "workspace_violation": {"type": "boolean"},
            },
        },
        "result": {
            "type": "object",
            "required": ["success", "failure_category", "execution_time_s", "path_length_m", "retries"],
            "properties": {
                "success": {"type": "boolean"},
                "failure_category": {
                    "enum": [
                        "unreachable",
                        "joint_limit",
                        "collision",
                        "slip",
                        "tracking_error",
                        "verifier_uncertain",
                        "reset_failure",
                        "mechanical_fault",
                        "other",
                        None,
                    ]
                },
                "execution_time_s": {"type": ["number", "null"]},
                "path_length_m": {"type": ["number", "null"]},
                "retries": {"type": "integer", "minimum": 0},
            },
        },
        "metadata": {"type": "object"},
    },
}


def validate_trial(record: dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL - set(record)
    if missing:
        raise ValueError(f"trial record missing top-level keys: {sorted(missing)}")
    perturbation_missing = REQUIRED_PERTURBATION - set(record["perturbation"])
    if perturbation_missing:
        raise ValueError(f"trial record missing perturbation keys: {sorted(perturbation_missing)}")
    if record["phase"] not in {"simulation", "hardware"}:
        raise ValueError(f"invalid phase: {record['phase']}")
    if record["verifier"]["label"] not in {"success", "failure", "uncertain"}:
        raise ValueError(f"invalid verifier label: {record['verifier']['label']}")
    if not isinstance(record["result"]["success"], bool):
        raise ValueError("result.success must be a boolean")
    if "path_length_m" not in record["result"]:
        raise ValueError("result.path_length_m is required")


def validate_trial_jsonschema(record: dict[str, Any]) -> None:
    """Validate against the formal JSON Schema when jsonschema is installed."""

    import jsonschema

    jsonschema.validate(instance=record, schema=TRIAL_JSON_SCHEMA)
