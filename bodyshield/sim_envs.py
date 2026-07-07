"""Optional high-fidelity simulator availability checks."""

from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SimEnvStatus:
    engine: str
    import_name: str
    installed: bool
    role: str
    status: str


def check_sim_envs() -> list[dict[str, str | bool]]:
    specs = [
        ("mujoco", "mujoco", "high-fidelity contact/dynamics follow-up"),
        ("maniskill", "mani_skill", "manipulation benchmark follow-up"),
        ("gymnasium", "gymnasium", "common evaluation environment wrapper"),
    ]
    rows = []
    for engine, import_name, role in specs:
        installed = importlib.util.find_spec(import_name) is not None
        status = "available" if installed else "not installed in this local run"
        rows.append(asdict(SimEnvStatus(engine, import_name, installed, role, status)))
    return rows
