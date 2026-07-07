from pathlib import Path


def test_reproducibility_manifest_present():
    assert Path("reports/REPRODUCIBILITY_MANIFEST.md").exists()
    assert Path("release/bodyshield_non_hardware_release.zip").exists() or Path("RELEASE_BUNDLE_MANIFEST.csv").exists()
