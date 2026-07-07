# Pack Verification

Status: `pass`

Code version: `b283a7c310f9ae04`

PACK_VERIFICATION, ARTIFACT_INVENTORY_AUDIT, PORTABLE_HYGIENE_AUDIT, RELEASE_PAYLOAD_AUDIT, RELEASE_DETERMINISM_AUDIT, and RELEASE_RUNTIME_AUDIT reports are excluded from ARTIFACT_MANIFEST to avoid self-referential hash churn.

| check | status | detail |
|---|---|---|
| required_artifacts | pass | 63 required artifacts exist and are nonempty |
| artifact_manifest | pass | rows=178; code_version=b283a7c310f9ae04; hashes and required rows match |
| paper_pdf | pass | 3 pages; safe structure; citations resolved; synthetic-media boundary present |
| paper_build_log | pass | final TeX logs contain no unresolved citation/reference warnings |
| synthetic_gifs | pass | bodyshield_synthetic_nominal_reference.gif=19; bodyshield_synthetic_bodybreak_failure.gif=19; bodyshield_synthetic_bodyshield_repair.gif=19 |
| simulation_rollout_videos | pass | 3 synthetic rollout rows with explicit evidence boundary |
| external_policy_readiness | pass | rows=2; fixture_smoke_passed=1; missing_checkpoint=1 |
| real_video_wam_readiness | pass | rows=2; fixture_training_smoke_passed=1; missing_dataset=1 |
| corrective_trace_readiness | pass | rows=2; fixture_fit_smoke_passed=1; missing_dataset=1 |
| release_bundle | pass | payload_files=252; zip_bytes=14051127; zip_sha256=9c355589957e2e6754998f7a1ec5c2a0f923e65afc8a48f9d6e3aee76dcbf817 |
| evidence_consistency | pass | rows=681; documents=7; all referenced local evidence exists |
| environment_dependency_audit | pass | rows=16; required dependencies/tools present and declared |
| config_schema_audit | pass | checks=40; artifacts=10; config and schema contracts pass |
| derived_results_audit | pass | checks=16; artifacts=6; derived tables recompute from primary trials |
| results_integrity_audit | pass | checks=301; artifacts=51; generated tables pass integrity checks |
| source_import_audit | pass | checks=157; artifacts=113; source compile/import and hardware-stub safety pass |
| artifact_inventory_audit | pass | checks=996; artifacts=150; documented outputs and manifests are synchronized |
| paper_source_audit | pass | checks=20; artifacts=5; paper source/build/PDF links pass integrity checks |
| portable_hygiene_audit | pass | checks=14; artifacts=7; text and release ZIP hygiene pass |
| claim_boundary_audit | pass | checks=63; artifacts=15; claim boundaries preserved |
| command_surface_audit | pass | checks=237; commands=23; documented commands callable and synchronized |
| visual_artifact_audit | pass | checks=156; artifacts=43; figures and GIF media pass integrity checks |
| release_payload_audit | pass | checks=11; artifacts=5; extracted payload verifier passes |
| release_determinism_audit | pass | checks=17; artifacts=5; release ZIP bytes are reproducible |
| release_runtime_audit | pass | checks=6; artifacts=3; extracted pytest passed=54 |
| stale_phrases | pass | no stale downgrade phrases in 160 text files |
