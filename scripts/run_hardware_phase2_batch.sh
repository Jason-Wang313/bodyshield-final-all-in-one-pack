#!/usr/bin/env bash
set -euo pipefail
python -m bodyshield.robot.run_batch --config "${1:-configs/hardware_push_block_phase2.yaml}" --autonomous --require-safety-green
