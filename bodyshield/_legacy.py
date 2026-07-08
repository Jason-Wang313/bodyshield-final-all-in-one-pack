"""Helpers for compatibility packages that shadow legacy module files."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_legacy_module(public_name: str, file_name: str) -> ModuleType:
    """Load a sibling legacy module file under a private module name."""

    package_root = Path(__file__).resolve().parent
    module_name = f"bodyshield._legacy_{public_name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, package_root / file_name)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load legacy module {file_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

