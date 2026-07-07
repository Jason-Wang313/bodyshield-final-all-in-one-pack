| method_id            |   nominal_success |   robustness_radius |   breaking_success_rate | breaking_perturbation                                |
|:---------------------|------------------:|--------------------:|------------------------:|:-----------------------------------------------------|
| nominal              |             0.917 |               0.331 |                   0.583 | latency_ms=40;calibration_offset_mm=10               |
| domain_randomization |             0.9   |               0.417 |                   0.6   | latency_ms=80;action_noise_std=0.01                  |
| random_tuning        |             0.833 |               0.3   |                   0.567 | latency_ms=40;action_noise_std=0.01                  |
| grid_worstcase       |             0.85  |               0.457 |                   0.6   | acceleration_cap_scale=0.75;calibration_offset_mm=10 |
| robust_control       |             0.8   |               0.331 |                   0.55  | latency_ms=40;calibration_offset_mm=10               |
| sysid_retune         |             0.817 |               0.667 |                   0.617 | latency_ms=160                                       |
| oracle               |             0.917 |               0.363 |                   0.817 | gripper_limit_scale=0.8;calibration_offset_mm=5      |
| human_effect_prior   |             0.967 |               0.439 |                   0.533 | latency_ms=80;calibration_offset_mm=10               |
| epec                 |             0.883 |               0.576 |                   0.533 | calibration_offset_mm=10;camera_shift_px=40          |
| bodyshield           |             0.883 |               0.5   |                   0.633 | latency_ms=120                                       |