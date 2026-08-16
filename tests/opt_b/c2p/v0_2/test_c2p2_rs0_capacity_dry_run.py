from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts/opt_b/c2p_v0_2/measure_rs0_capacity_dry_run.py"
BINDING = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_EXTERNAL_ARTIFACT_ROOT_BINDING_v0_1.json"
REQUEST = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CAPACITY_DRY_RUN_REQUEST_v0_1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("c2p2_rs0_capacity_dry_run", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capacity_request_preserves_non_evidentiary_firewall():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    assert request["status"] == "MEASUREMENT_REQUESTED_NON_EVIDENTIARY"
    assert request["real_source_execution"] == "FORBIDDEN"
    assert request["validation"] == "LOCKED_UNCONSUMED"
    assert request["measurement_firewall"]["synthetic_only"] is True
    assert request["reference_envelope"] == {
        "eligible_candidates_max": 2048,
        "identity_predicates_max": 16,
        "pair_adjudications_max": 4194304,
    }


def test_external_artifact_root_is_exact_and_non_authoritative():
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    assert binding["status"] == "BOUND_PRE_RUN"
    assert binding["canonical_external_artifacts_root"]["folder_id"] == "1s-I8kQkelxB1ZYS0vKVKCeNL1XZSBdZS"
    assert binding["rs0_root"]["folder_id"] == "1AkfK95_GB5Oz7U_PC5wA7rUWZAfcGhvv"
    assert binding["rs0_root"]["parent_folder_id"] == binding["canonical_external_artifacts_root"]["folder_id"]
    assert binding["write_boundary"]["real_source_write"] == "DENIED_UNTIL_C2P2_RS0_GRUN_OPERATOR_PASS"


def test_measurement_harness_uses_synthetic_pack_and_exact_restart_on_small_fixture():
    module = load_module()
    pack = json.loads(module.PACK_PATH.read_text(encoding="utf-8"))
    assert pack["status"] == "SYNTHETIC_ONLY_NONEMPIRICAL"
    assert pack["real_source_forbidden"] is True
    kernel_digest, pair_count = module._pair_kernel(candidate_count=16)
    assert len(kernel_digest) == 64
    assert pair_count == 120
    ledger, assertion_ids = module._build_ledger(pack, count=8)
    assert ledger.event_count == 8
    assert len(assertion_ids) == 8
