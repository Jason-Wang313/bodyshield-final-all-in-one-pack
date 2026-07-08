# Release Runtime Audit

Status: `pass`

This audit safely extracts the portable release ZIP and runs the bundled pytest suite from inside the extracted archive. It verifies that the release is not only checksum-valid and byte-reproducible, but also executable as a standalone local test payload.

| metric | value |
|---|---:|
| checks | 6 |
| passed | 6 |
| failed | 0 |
| artifacts audited | 3 |

## Display Rows

| artifact                                    | check                                | status   | detail                                             | observed     | expected     |
|:--------------------------------------------|:-------------------------------------|:---------|:---------------------------------------------------|:-------------|:-------------|
| release/bodyshield_non_hardware_release.zip | release_zip_exists_nonempty          | pass     | release ZIP exists and is nonempty                 | 15341205     | >0 bytes     |
| release/bodyshield_non_hardware_release.zip | zip_extracts_safely                  | pass     | release ZIP entries extract without unsafe paths   | 475          | >0 entries   |
| tests                                       | extracted_tests_present              | pass     | extracted release contains pytest tests            | 14           | >0           |
| tests                                       | extracted_pytest_returncode          | pass     | pytest exits successfully inside extracted release | returncode=0 | returncode=0 |
| tests                                       | extracted_pytest_passed_count        | pass     | pytest output reports passing tests                | 67           | >0           |
| tmp                                         | temporary_runtime_extraction_cleaned | pass     | temporary runtime extraction directory removed     |              |              |
