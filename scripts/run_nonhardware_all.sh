#!/usr/bin/env bash
set -euo pipefail
python scripts/run_non_hardware.py
python scripts/finalize_nonrejectable_artifacts.py
python scripts/finalize_maxout_artifacts.py
