PYTHON ?= python

.PHONY: smoke test reproduce-minimal reproduce-sim-main reproduce-main-figures paper package-artifacts final-check

smoke:
	$(PYTHON) scripts/smoke_check.py
	$(PYTHON) scripts/run_source_import_audit.py --json
	$(PYTHON) scripts/run_command_surface_audit.py --json

test:
	$(PYTHON) -m pytest -q

reproduce-minimal:
	$(PYTHON) scripts/finalize_maxout_artifacts.py
	$(PYTHON) scripts/run_derived_results_audit.py --json
	$(PYTHON) scripts/run_results_integrity_audit.py --json
	$(PYTHON) scripts/run_paper_source_audit.py --json
	$(PYTHON) scripts/verify_non_hardware_pack.py --write-reports --json

reproduce-sim-main:
	$(PYTHON) scripts/run_non_hardware.py
	$(PYTHON) scripts/finalize_maxout_artifacts.py

reproduce-main-figures:
	$(PYTHON) scripts/run_visual_artifact_audit.py --json

paper:
	$(PYTHON) scripts/build_bodyshield_icra_paper.py
	$(PYTHON) scripts/run_paper_source_audit.py --json

package-artifacts:
	$(PYTHON) scripts/finalize_maxout_artifacts.py
	$(PYTHON) -c "import shutil; shutil.rmtree('paper/build_icra', ignore_errors=True)"
	$(PYTHON) scripts/build_release_bundle.py --json
	$(PYTHON) scripts/run_release_payload_audit.py --json
	$(PYTHON) scripts/run_release_determinism_audit.py --json
	$(PYTHON) scripts/run_release_runtime_audit.py --json
	$(PYTHON) scripts/verify_non_hardware_pack.py --write-reports --json

final-check: smoke test reproduce-minimal paper package-artifacts
