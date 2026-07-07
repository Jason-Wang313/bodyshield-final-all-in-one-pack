# Safe Robot API Specification

The robot API must expose bounded primitives only.

## Allowed primitives

```python
reset_to_home()
open_gripper()
close_gripper(max_effort=None, timeout_s=2.0)
move_to_pose(x, y, z, roll, pitch, yaw, speed_scale=0.3)
move_relative(dx, dy, dz, droll=0, dpitch=0, dyaw=0, speed_scale=0.3)
attempt_push(start_pose, end_pose, speed_scale=0.2)
attempt_press(target_pose, speed_scale=0.15)
attempt_grasp(pre_pose, grasp_pose, lift_pose, speed_scale=0.2)
attempt_pull(contact_pose, pull_vector, speed_scale=0.15)
stop_now()
```

## Primitive-level safety constraints

Every primitive must check:
- joint limits
- workspace limits
- speed limits
- acceleration limits
- gripper limits
- current/load thresholds if available
- timeout
- camera visibility if required
- return-to-home feasibility

## Forbidden

- raw joint velocity command from LLM
- raw torque command from LLM
- disabling safety checks
- dynamic workspace expansion during batch
- any primitive not dry-run tested
- repeated collision retries without pause
- unattended batch without explicit config flag

## Perturbation implementation rules

Perturbations must be applied by wrapper, not by direct unsafe motor commands.

Examples:
- latency: delay high-level primitive execution by controlled buffer
- action noise: perturb target pose within safe envelope
- joint range: clamp planner limits before IK
- gripper limit: clamp gripper open/close command
- speed cap: reduce speed_scale
- calibration offset: apply transform perturbation in planning layer
- camera shift: controlled crop/extrinsic transform, or physical camera move with recalibration
- payload/tool extension: physical setup requires user confirmation and new safety check
