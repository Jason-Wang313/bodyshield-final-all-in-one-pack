#!/usr/bin/env bash
set -euo pipefail
python scripts/build_paper_targets.py
python scripts/build_bodyshield_icra_paper.py
