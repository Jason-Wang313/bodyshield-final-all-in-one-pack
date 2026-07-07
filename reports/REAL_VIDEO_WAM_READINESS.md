# Real-Video WAM Readiness

This report validates the local frame-manifest, action-label, centroid-feature, and tiny predictor-fit path needed before future real-camera WAM experiments.

It is not real-video WAM evidence, foundation-model training, or physical transfer evidence. With the included example spec, no real camera dataset is present.

## Summary
- Rows: 2
- Fixture training-smoke rows passed: 1
- Real-video dataset specs: 1
- Real-frame manifest smokes executed: 0
- Missing real-video datasets: 1
- Failed rows: 0

## Rows
| benchmark_name                      | dataset_id                        | source             | dataset_root                                     | manifest_path                                                 | status                        | dataset_present   | manifest_present   | training_smoke_passed   |   action_dim |   frames_checked |   transitions |   baseline_next_centroid_mse |   fitted_next_centroid_mse |   mean_action_norm | evidence_boundary                                                                              | notes                                                                                                                                                                                       |
|:------------------------------------|:----------------------------------|:-------------------|:-------------------------------------------------|:--------------------------------------------------------------|:------------------------------|:------------------|:-------------------|:------------------------|-------------:|-----------------:|--------------:|-----------------------------:|---------------------------:|-------------------:|:-----------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| bodyshield_real_video_wam_readiness | fixture_manifest_sequence         | fixture_sequence   |                                                  |                                                               | fixture_training_smoke_passed | False             | False              | True                    |            2 |                8 |             7 |                    0.0047619 |                0.000383142 |          0.0923724 | Synthetic fixture frame-manifest smoke only; not real camera video or foundation WAM training. | Deterministic generated frame-manifest smoke used to prove the ingestion and fit path executes.                                                                                             |
| bodyshield_real_video_wam_readiness | replace_with_real_camera_sequence | real_video_dataset | external_real_video/replace_with_camera_sequence | external_real_video/replace_with_camera_sequence/manifest.csv | missing_dataset               | False             | False              | False                   |            2 |                0 |             0 |                  nan         |              nan           |        nan         | No real-video WAM evidence was generated because the dataset path or manifest is missing.      | Template row: replace with extracted real camera frames and action labels before claiming real-video WAM evidence. Dataset root or manifest not found; real-video WAM training was not run. |

## Safe claim
The pack now has a runnable readiness harness for real-video WAM data ingestion and tiny fit validation. The included example real-video dataset is missing, so no real-video or foundation-scale WAM claim is supported.
