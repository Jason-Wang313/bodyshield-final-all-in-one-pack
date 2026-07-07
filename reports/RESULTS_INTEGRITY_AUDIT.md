# Results Integrity Audit

Status: `pass`

This audit checks generated result tables for parseability, nonempty rows, duplicate-column corruption, expected row counts, required columns, key uniqueness, required categorical values, numeric ranges, JSONL sample shape, schema-summary counts, and Parquet row-count agreement.

| metric | value |
|---|---:|
| checks | 301 |
| passed | 301 |
| failed | 0 |
| artifacts audited | 51 |

## Display Rows

| artifact                                           | check               | status   | detail                     | observed               | expected   |
|:---------------------------------------------------|:--------------------|:---------|:---------------------------|:-----------------------|:-----------|
| results/bodybreak_minimality_audit.csv             | csv_exists_nonempty | pass     | CSV exists and is nonempty | 5355                   | >0 bytes   |
| results/bodybreak_minimality_audit.csv             | csv_parse           | pass     | CSV parsed                 | 12 rows; 19 columns    |            |
| results/bodybreak_minimality_audit.csv             | csv_nonempty_rows   | pass     | CSV has data rows          | 12                     | >0         |
| results/bodybreak_minimality_audit.csv             | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/breaking_search.csv                        | csv_exists_nonempty | pass     | CSV exists and is nonempty | 55246                  | >0 bytes   |
| results/breaking_search.csv                        | csv_parse           | pass     | CSV parsed                 | 288 rows; 10 columns   |            |
| results/breaking_search.csv                        | csv_nonempty_rows   | pass     | CSV has data rows          | 288                    | >0         |
| results/breaking_search.csv                        | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/claim_boundary_audit.csv                   | csv_exists_nonempty | pass     | CSV exists and is nonempty | 9038                   | >0 bytes   |
| results/claim_boundary_audit.csv                   | csv_parse           | pass     | CSV parsed                 | 63 rows; 6 columns     |            |
| results/claim_boundary_audit.csv                   | csv_nonempty_rows   | pass     | CSV has data rows          | 63                     | >0         |
| results/claim_boundary_audit.csv                   | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/command_surface_audit.csv                  | csv_exists_nonempty | pass     | CSV exists and is nonempty | 41424                  | >0 bytes   |
| results/command_surface_audit.csv                  | csv_parse           | pass     | CSV parsed                 | 237 rows; 8 columns    |            |
| results/command_surface_audit.csv                  | csv_nonempty_rows   | pass     | CSV has data rows          | 237                    | >0         |
| results/command_surface_audit.csv                  | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/config_schema_audit.csv                    | csv_exists_nonempty | pass     | CSV exists and is nonempty | 6161                   | >0 bytes   |
| results/config_schema_audit.csv                    | csv_parse           | pass     | CSV parsed                 | 40 rows; 6 columns     |            |
| results/config_schema_audit.csv                    | csv_nonempty_rows   | pass     | CSV has data rows          | 40                     | >0         |
| results/config_schema_audit.csv                    | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/corrective_adaptation_eval.csv             | csv_exists_nonempty | pass     | CSV exists and is nonempty | 2565                   | >0 bytes   |
| results/corrective_adaptation_eval.csv             | csv_parse           | pass     | CSV parsed                 | 12 rows; 11 columns    |            |
| results/corrective_adaptation_eval.csv             | csv_nonempty_rows   | pass     | CSV has data rows          | 12                     | >0         |
| results/corrective_adaptation_eval.csv             | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/corrective_adaptation_residual_weights.csv | csv_exists_nonempty | pass     | CSV exists and is nonempty | 4103                   | >0 bytes   |
| results/corrective_adaptation_residual_weights.csv | csv_parse           | pass     | CSV parsed                 | 52 rows; 4 columns     |            |
| results/corrective_adaptation_residual_weights.csv | csv_nonempty_rows   | pass     | CSV has data rows          | 52                     | >0         |
| results/corrective_adaptation_residual_weights.csv | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/corrective_adaptation_rollouts.csv         | csv_exists_nonempty | pass     | CSV exists and is nonempty | 1465486                | >0 bytes   |
| results/corrective_adaptation_rollouts.csv         | csv_parse           | pass     | CSV parsed                 | 6912 rows; 14 columns  |            |
| results/corrective_adaptation_rollouts.csv         | csv_nonempty_rows   | pass     | CSV has data rows          | 6912                   | >0         |
| results/corrective_adaptation_rollouts.csv         | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/corrective_trace_readiness.csv             | csv_exists_nonempty | pass     | CSV exists and is nonempty | 1251                   | >0 bytes   |
| results/corrective_trace_readiness.csv             | csv_parse           | pass     | CSV parsed                 | 2 rows; 16 columns     |            |
| results/corrective_trace_readiness.csv             | csv_nonempty_rows   | pass     | CSV has data rows          | 2                      | >0         |
| results/corrective_trace_readiness.csv             | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/derived_results_audit.csv                  | csv_exists_nonempty | pass     | CSV exists and is nonempty | 2679                   | >0 bytes   |
| results/derived_results_audit.csv                  | csv_parse           | pass     | CSV parsed                 | 16 rows; 6 columns     |            |
| results/derived_results_audit.csv                  | csv_nonempty_rows   | pass     | CSV has data rows          | 16                     | >0         |
| results/derived_results_audit.csv                  | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/environment_dependency_audit.csv           | csv_exists_nonempty | pass     | CSV exists and is nonempty | 2001                   | >0 bytes   |
| results/environment_dependency_audit.csv           | csv_parse           | pass     | CSV parsed                 | 16 rows; 11 columns    |            |
| results/environment_dependency_audit.csv           | csv_nonempty_rows   | pass     | CSV has data rows          | 16                     | >0         |
| results/environment_dependency_audit.csv           | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/evidence_consistency_audit.csv             | csv_exists_nonempty | pass     | CSV exists and is nonempty | 70495                  | >0 bytes   |
| results/evidence_consistency_audit.csv             | csv_parse           | pass     | CSV parsed                 | 681 rows; 5 columns    |            |
| results/evidence_consistency_audit.csv             | csv_nonempty_rows   | pass     | CSV has data rows          | 681                    | >0         |
| results/evidence_consistency_audit.csv             | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/external_policy_benchmark_readiness.csv    | csv_exists_nonempty | pass     | CSV exists and is nonempty | 1239                   | >0 bytes   |
| results/external_policy_benchmark_readiness.csv    | csv_parse           | pass     | CSV parsed                 | 2 rows; 20 columns     |            |
| results/external_policy_benchmark_readiness.csv    | csv_nonempty_rows   | pass     | CSV has data rows          | 2                      | >0         |
| results/external_policy_benchmark_readiness.csv    | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/failure_taxonomy_counts.csv                | csv_exists_nonempty | pass     | CSV exists and is nonempty | 2693                   | >0 bytes   |
| results/failure_taxonomy_counts.csv                | csv_parse           | pass     | CSV parsed                 | 90 rows; 3 columns     |            |
| results/failure_taxonomy_counts.csv                | csv_nonempty_rows   | pass     | CSV has data rows          | 90                     | >0         |
| results/failure_taxonomy_counts.csv                | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/high_fidelity_benchmark.csv                | csv_exists_nonempty | pass     | CSV exists and is nonempty | 126789                 | >0 bytes   |
| results/high_fidelity_benchmark.csv                | csv_parse           | pass     | CSV parsed                 | 594 rows; 19 columns   |            |
| results/high_fidelity_benchmark.csv                | csv_nonempty_rows   | pass     | CSV has data rows          | 594                    | >0         |
| results/high_fidelity_benchmark.csv                | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/learned_outcome_axis_weights.csv           | csv_exists_nonempty | pass     | CSV exists and is nonempty | 1485                   | >0 bytes   |
| results/learned_outcome_axis_weights.csv           | csv_parse           | pass     | CSV parsed                 | 15 rows; 3 columns     |            |
| results/learned_outcome_axis_weights.csv           | csv_nonempty_rows   | pass     | CSV has data rows          | 15                     | >0         |
| results/learned_outcome_axis_weights.csv           | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/learned_outcome_model_eval.csv             | csv_exists_nonempty | pass     | CSV exists and is nonempty | 893                    | >0 bytes   |
| results/learned_outcome_model_eval.csv             | csv_parse           | pass     | CSV parsed                 | 6 rows; 8 columns      |            |
| results/learned_outcome_model_eval.csv             | csv_nonempty_rows   | pass     | CSV has data rows          | 6                      | >0         |
| results/learned_outcome_model_eval.csv             | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/learned_outcome_predictions.csv            | csv_exists_nonempty | pass     | CSV exists and is nonempty | 3090676                | >0 bytes   |
| results/learned_outcome_predictions.csv            | csv_parse           | pass     | CSV parsed                 | 23040 rows; 10 columns |            |
| results/learned_outcome_predictions.csv            | csv_nonempty_rows   | pass     | CSV has data rows          | 23040                  | >0         |
| results/learned_outcome_predictions.csv            | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/method_deltas_vs_bodyshield.csv            | csv_exists_nonempty | pass     | CSV exists and is nonempty | 6590                   | >0 bytes   |
| results/method_deltas_vs_bodyshield.csv            | csv_parse           | pass     | CSV parsed                 | 27 rows; 15 columns    |            |
| results/method_deltas_vs_bodyshield.csv            | csv_nonempty_rows   | pass     | CSV has data rows          | 27                     | >0         |
| results/method_deltas_vs_bodyshield.csv            | csv_unique_columns  | pass     | column names are unique    |                        |            |
| results/mujoco_residual_policy_eval.csv            | csv_exists_nonempty | pass     | CSV exists and is nonempty | 1956                   | >0 bytes   |
| results/mujoco_residual_policy_eval.csv            | csv_parse           | pass     | CSV parsed                 | 9 rows; 14 columns     |            |
| results/mujoco_residual_policy_eval.csv            | csv_nonempty_rows   | pass     | CSV has data rows          | 9                      | >0         |
| results/mujoco_residual_policy_eval.csv            | csv_unique_columns  | pass     | column names are unique    |                        |            |
