# Release Payload Audit

Status: `pass`

This audit safely extracts the portable release ZIP, runs the bundled unpacked-payload verifier from inside the extracted archive, and compares its payload counts with pack-side release inspection. It treats `RELEASE_BUNDLE_MANIFEST.csv` as the archive inventory; `reports/ARTIFACT_MANIFEST.csv` is a pack-side full-pack inventory and is intentionally not the release payload manifest.

| metric | value |
|---|---:|
| checks | 11 |
| passed | 11 |
| failed | 0 |
| artifacts audited | 5 |

## Display Rows

| artifact                                    | check                                                | status   | detail                                                                                                              | observed                                           | expected          |
|:--------------------------------------------|:-----------------------------------------------------|:---------|:--------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------|:------------------|
| release/bodyshield_non_hardware_release.zip | release_zip_exists_nonempty                          | pass     | release ZIP exists and is nonempty                                                                                  | 15371661                                           | >0 bytes          |
| release/bodyshield_non_hardware_release.zip | pack_side_release_inspection_status                  | pass     | pack-side release bundle inspection passes                                                                          | pass                                               | pass              |
| release/bodyshield_non_hardware_release.zip | zip_integrity_test                                   | pass     | zipfile CRC test passes                                                                                             | None                                               | None              |
| release/bodyshield_non_hardware_release.zip | zip_extracts_safely                                  | pass     | release ZIP entries extract without unsafe paths                                                                    | 434                                                | >0 entries        |
| scripts/verify_release_payload.py           | bundled_verifier_exists_nonempty                     | pass     | bundled payload verifier exists after extraction                                                                    | True                                               | True              |
| scripts/verify_release_payload.py           | bundled_verifier_json_status                         | pass     | bundled verifier runs from extracted payload and returns pass JSON                                                  | pass                                               | pass              |
| RELEASE_BUNDLE_MANIFEST.csv                 | extracted_payload_file_count_matches_pack_inspection | pass     | extracted verifier file count matches pack-side release inspection                                                  | 432                                                | 432               |
| RELEASE_BUNDLE_MANIFEST.csv                 | extracted_payload_bytes_match_pack_inspection        | pass     | extracted verifier payload bytes match pack-side release inspection                                                 | 372459155                                          | 372459155         |
| RELEASE_BUNDLE_MANIFEST.csv                 | zip_entry_count_matches_manifest_plus_control_files  | pass     | zip entries equal payload manifest rows plus release README and release manifest                                    | 434                                                | 434               |
| reports/ARTIFACT_MANIFEST.csv               | full_pack_manifest_boundary_documented               | pass     | release validation uses RELEASE_BUNDLE_MANIFEST.csv; reports/ARTIFACT_MANIFEST.csv is pack-side full-pack inventory | release payload manifest authoritative for archive | boundary explicit |
| tmp                                         | temporary_extraction_cleaned                         | pass     | temporary extraction directories removed                                                                            |                                                    |                   |
