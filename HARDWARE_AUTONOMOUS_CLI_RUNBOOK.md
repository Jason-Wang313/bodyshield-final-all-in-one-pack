# Hardware Autonomous CLI Runbook

This document tells the CLI agent how to run SO-ARM101/SO-101 hardware experiments automatically.

## 0. Safety principle

The CLI agent may schedule and analyze hardware experiments, but it must never send raw motor commands.

Hardware motion must pass through:
1. bounded safe primitives;
2. workspace limits;
3. speed/current/load/timeout limits;
4. verifier/reset checks;
5. emergency stop;
6. batch-level human approval until safety is proven.

## 1. Autonomy levels

### Level 0 — no hardware
Simulation, code, plots, paper skeleton. This is the default.

### Level 1 — supervised hardware dry run
User present. One trial at a time. CLI agent can call bounded primitives but must pause after each trial.

### Level 2 — supervised autonomous batch
User present or immediately available. CLI agent launches batch of 10–50 trials. Safety gate and emergency stop required.

### Level 3 — unattended autonomous batch
Allowed only after:
- 500+ safe supervised trials;
- zero critical safety stops in last 200 trials;
- verifier >95% agreement with human audit;
- reset reliability >95%;
- thermal/current behavior stable;
- user explicitly enables unattended mode in config.
Even then, batch must stop every 50 trials for health checks.

Recommended target: Level 2 for paper experiments. Level 3 only if the setup is proven safe.

## 2. Required physical setup

- SO-ARM101/SO-101 assembled and calibrated.
- Stable table.
- Clear workspace.
- Camera fixed overhead or multi-view.
- Emergency stop physically tested.
- Power supply matches hardware requirements.
- Robot can return to safe home without collision.
- Physical fixtures installed for self-reset tasks where possible:
  - target mat
  - rails
  - return ramp
  - bin
  - button mount
  - ring/drawer return spring
  - object boundaries
- All moving objects are light and non-hazardous.
- No humans/pets in workspace during autonomous batches.

## 3. CLI commands to implement

### Hardware health check

```
python -m bodyshield.robot.healthcheck \
  --robot-id so101_follower \
  --port /dev/ttyACM0 \
  --camera overhead
```

Checks:
- motor connection
- calibration file exists
- camera connected
- home pose reachable
- e-stop detected
- workspace limits loaded
- safe primitive execution in air

### Safety gate

```
python -m bodyshield.robot.safety_gate --check-all
```

Checks:
- workspace boundary
- speed limits
- joint limits
- current/load thresholds
- timeout thresholds
- stop-now command
- recovery-to-home
- no raw-command path exposed
- log directory writable

### Noise floor calibration

```
python -m bodyshield.robot.calibrate_noise_floor \
  --task push_block \
  --trials 30 \
  --config configs/hardware/push_block_base.yaml
```

Outputs:
- repeatability
- tracking error
- verifier agreement
- baseline failure rate
- drift over time

### Autonomous batch

```
python -m bodyshield.robot.run_batch \
  --config configs/hardware/phase2_bodyshield_push.yaml \
  --autonomous \
  --require-safety-green \
  --max-trials 50 \
  --pause-on-safety-event \
  --pause-on-verifier-uncertainty \
  --write-batch-report
```

### Batch analysis

```
python -m bodyshield.analysis.summarize_batch \
  --batch-dir logs/hardware/<batch_id> \
  --write-report reports/hardware/<batch_id>.md
```

## 4. Batch stop conditions

The batch must stop immediately if any happens:
- emergency stop pressed
- workspace violation predicted
- current/load exceeds threshold
- joint tracking error exceeds threshold
- camera verifier uncertain for 3 consecutive trials
- reset failure for 2 consecutive trials
- collision detected or suspected
- robot fails to return home
- temperature/current trend abnormal
- log write fails
- user sends stop command
- policy attempts unapproved primitive

## 5. Autonomous reset strategy

Prefer tasks with automatic reset:
- Push block: rail + return ramp or bounded manual tray reset.
- Button press: spring-return button.
- Slide track: sloped/elastic return.
- Ring pull: elastic return.
- Drawer: spring/elastic return or bounded manual reset.
- Pick-to-bin: bin with return tray; if not feasible, use manual reset and mark as such.

Every reset must be verified before the next trial:
- object in initial region;
- robot at home;
- camera visible;
- no obstruction;
- verifier confidence high.

## 6. Verifier design

Use simple robust verification first:
- ArUco markers;
- colored object masks;
- target zone occupancy;
- button state visual marker;
- drawer/ring displacement marker;
- bin occupancy.

Every verifier must report:
- success label;
- confidence;
- reason;
- raw measurement;
- image/video path.

Human audit:
- 100% audit for first 100 trials.
- 20% random audit after verifier reaches >95% agreement.
- Audit every uncertain case.

## 7. Agent behavior during hardware

The CLI agent may:
- choose next config from approved experiment matrix;
- run batches;
- analyze logs;
- propose perturbation search updates;
- update policy parameters;
- generate reports and plots.

The CLI agent may not:
- bypass safety shield;
- change workspace limits without user approval;
- increase speed/current/load limits without user approval;
- run new primitives without dry-run approval;
- continue after stop condition.

## 8. Hardware artifacts to save

For every trial:
- config hash
- code commit hash
- task id
- policy id
- perturbation vector
- action trace
- joint target/state logs
- camera images/video
- verifier label/confidence
- human audit label if available
- safety events
- reset status
- success/failure category
- notes

For every batch:
- summary table
- safety summary
- verifier audit summary
- hardware health summary
- plots
- next-batch recommendation
