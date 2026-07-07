#!/usr/bin/env bash
set -euo pipefail
python -m bodyshield.robot.healthcheck
python -m bodyshield.robot.safety_gate --check-all
