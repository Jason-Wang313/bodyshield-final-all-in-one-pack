PYTHON ?= python

.PHONY: smoke test nonhardware post-nonhardware external-policy-public-env reproduce-minimal reproduce-sim-main reproduce-main-figures sim-minimal sim-full paper verify package-artifacts final-check

smoke:
	$(PYTHON) scripts/smoke_check.py
	$(PYTHON) scripts/verify_claims.py
	$(PYTHON) scripts/verify_citations.py
	$(PYTHON) scripts/verify_reproducibility.py
	$(PYTHON) -m bodyshield.analysis.verify_package --json
	$(PYTHON) scripts/run_source_import_audit.py --json
	$(PYTHON) scripts/run_command_surface_audit.py --json

test:
	$(PYTHON) -m pytest -q

reproduce-minimal:
	$(PYTHON) scripts/finalize_nonrejectable_artifacts.py
	$(PYTHON) scripts/finalize_maxout_artifacts.py
	$(PYTHON) scripts/finalize_v2_artifacts.py
	$(PYTHON) scripts/run_derived_results_audit.py --json
	$(PYTHON) scripts/run_results_integrity_audit.py --json
	$(PYTHON) scripts/run_paper_source_audit.py --json
	$(PYTHON) scripts/verify_non_hardware_pack.py --write-reports --json

reproduce-sim-main:
	$(PYTHON) scripts/run_non_hardware.py
	$(PYTHON) scripts/finalize_nonrejectable_artifacts.py
	$(PYTHON) scripts/finalize_maxout_artifacts.py
	$(PYTHON) scripts/finalize_v2_artifacts.py

nonhardware: reproduce-sim-main

post-nonhardware:
	$(PYTHON) scripts/finalize_v3_artifacts.py
	$(PYTHON) -m bodyshield.analysis.verify_package --json

external-policy-public-env:
	$(PYTHON) scripts/run_self_trained_public_env_benchmark.py
	$(PYTHON) -m bodyshield.analysis.verify_package --json

sim-minimal: reproduce-minimal

sim-full: reproduce-sim-main

reproduce-main-figures:
	$(PYTHON) scripts/run_visual_artifact_audit.py --json

paper:
	$(PYTHON) scripts/finalize_v2_artifacts.py
	$(PYTHON) scripts/build_paper_targets.py
	$(PYTHON) scripts/build_bodyshield_icra_paper.py
	$(PYTHON) scripts/run_paper_source_audit.py --json

verify:
	$(PYTHON) -m bodyshield.analysis.verify_package --json
	$(PYTHON) scripts/verify_non_hardware_pack.py --json
	$(PYTHON) scripts/verify_claims.py
	$(PYTHON) scripts/verify_citations.py
	$(PYTHON) scripts/verify_reproducibility.py

package-artifacts:
	$(PYTHON) scripts/finalize_nonrejectable_artifacts.py
	$(PYTHON) scripts/finalize_maxout_artifacts.py
	$(PYTHON) scripts/finalize_v2_artifacts.py
	$(PYTHON) scripts/finalize_v3_artifacts.py
	$(PYTHON) -c "import shutil; shutil.rmtree('paper/build_icra', ignore_errors=True)"
	$(PYTHON) scripts/build_release_bundle.py --json
	$(PYTHON) scripts/run_release_payload_audit.py --json
	$(PYTHON) scripts/run_release_determinism_audit.py --json
	$(PYTHON) scripts/run_release_runtime_audit.py --json
	$(PYTHON) scripts/verify_non_hardware_pack.py --write-reports --json

final-check: smoke test sim-minimal paper package-artifacts verify
