"""Task-suite metadata for non-hardware and future hardware execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TaskCard:
    task_id: str
    verifier: str
    reset_protocol: str
    safety_envelope: str
    oracle_policy: str
    primary_failure_modes: tuple[str, ...]


TASK_CARDS: tuple[TaskCard, ...] = (
    TaskCard(
        "push_block",
        "target-zone position check from object centroid",
        "reset block to start marker before every episode",
        "planar workspace bounds plus low speed cap",
        "straight-line guarded push with retuned contact point",
        ("slip", "tracking_error", "calibration_error"),
    ),
    TaskCard(
        "press_button",
        "button-state transition or target-contact event",
        "release button and return tool to approach pose",
        "approach cone around button normal",
        "calibrated guarded press along measured normal",
        ("calibration_error", "tracking_error", "joint_limit"),
    ),
    TaskCard(
        "slide_track",
        "object reaches track endpoint region",
        "return object to track start stop",
        "track-aligned corridor with contact force cap",
        "track-following controller with friction-aware speed",
        ("slip", "tracking_error", "reset_failure"),
    ),
    TaskCard(
        "pick_place_bin",
        "object centroid inside bin after gripper release",
        "object returned to pickup marker and bin emptied",
        "lift-height minimum plus bin collision envelope",
        "retuned grasp width and lift trajectory",
        ("unreachable", "joint_limit", "mechanical_fault"),
    ),
    TaskCard(
        "pull_ring",
        "ring/drawer displacement exceeds task threshold",
        "ring returned to fully closed position",
        "pull corridor and load/current cap",
        "quasi-static pull with retuned force margin",
        ("tracking_error", "mechanical_fault", "joint_limit"),
    ),
    TaskCard(
        "constrained_place",
        "object pose in target region without obstacle contact",
        "obstacle and object returned to fixture markers",
        "obstacle clearance margin and workspace bounds",
        "waypoint placement around measured obstacle",
        ("collision", "calibration_error", "joint_limit"),
    ),
    TaskCard(
        "tool_push",
        "tool tip pushes object into target zone",
        "tool removed and object returned to start marker",
        "tool-swept-volume envelope",
        "retuned tool-frame push trajectory",
        ("collision", "slip", "tracking_error"),
    ),
    TaskCard(
        "rotate_object",
        "object orientation within tolerance after contact",
        "object returned to canonical orientation",
        "contact patch and workspace envelope",
        "multi-contact rotate primitive with conservative speed",
        ("slip", "unreachable", "tracking_error"),
    ),
)


def task_cards_as_rows() -> list[dict[str, str]]:
    rows = []
    for card in TASK_CARDS:
        row = asdict(card)
        row["primary_failure_modes"] = ", ".join(card.primary_failure_modes)
        rows.append(row)
    return rows
