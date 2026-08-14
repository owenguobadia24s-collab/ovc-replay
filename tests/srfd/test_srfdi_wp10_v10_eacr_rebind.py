from __future__ import annotations

import json
from pathlib import Path

from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_v10_interface import (
    SCIENCE_IDENTITY_SHA256,
    binding_from_manifest,
    mint_single_use_token,
)
from tests.historical_court_record import json_at

ROOT = Path(__file__).resolve().parents[2]
SRFD_REL = ROOT / "docs/releases/srfd-benchmark-v0-1"
EACR_REL = ROOT / "docs/releases/external-artifact-capacity-ownership-v0-1"
REG = ROOT / "registries/research/srfd"
STATE = ROOT / "registries/implementation/srfd"

NEW_TOKEN = "SRFD.JUNE.AUTH.ba38ee329eba42c169420bb328956777b3604de4db35308fa306a9bda8711927"
OLD_PR558_TOKEN = "SRFD.JUNE.AUTH.49a8132414264699a3b72b81fb8f5c415417ba48fc0a6fd664eac4df0f1e5c6b"
DECISION_ID = "SRFDI-WP10-v1.0-EACR-REBIND-OPERATOR-AUTHORIZE-v1"


def j(path: Path):
    return json.loads(path.read_text())


def assert_logical(path: Path):
    data = j(path)
    expected = data.pop("logical_sha256")
    assert logical_sha256(data) == expected


def test_shared_storage_binding_is_not_srfd_owned_generic_infrastructure():
    binding = j(REG / "wp10_v10_storage_binding_v0_2.json")
    assert binding["ownership"]["physical_storage_owner"] == "OVC_EVIDENCE_STORE"
    assert binding["ownership"]["scientific_output_owner"] == "OVC-SRFD-BENCHMARK-v0.1"
    assert binding["ownership"]["run_authority_owner"] == "SRFD_GOVERNANCE"
    assert binding["shared_infrastructure"]["source_commit"] == "5231baebdfced4e889fc9ea64979be345d5e4102"
    assert binding["v09_reuse_boundary"]["old_checkpoint_relabel"] == "FORBIDDEN"
    assert_logical(REG / "wp10_v10_storage_binding_v0_2.json")


def test_execution_binding_preserves_science_and_records_only_prestart_correction():
    binding = j(REG / "wp10_v10_execution_binding_v0_2.json")
    assert binding["science_identity_sha256"] == SCIENCE_IDENTITY_SHA256
    assert binding["corrective_note"]["scientific_delta"] == "NONE"
    assert binding["corrective_note"]["correction"] == "use exact v09_root parameter"
    assert_logical(REG / "wp10_v10_execution_binding_v0_2.json")


def test_manifest_recomputes_exact_binding_and_token():
    manifest = j(SRFD_REL / "srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v1_0_EACR.json")
    binding = binding_from_manifest(manifest)
    assert binding.logical_hash == "e9f32060bb6f966db3a643192731bca1c13ed61e885c18e3cafda7e42b65a5ce"
    assert binding.science_identity_sha256 == SCIENCE_IDENTITY_SHA256
    minted = mint_single_use_token(binding, operator_decision_id=DECISION_ID)
    assert minted["token_id"] == NEW_TOKEN
    assert minted["state"] == "AUTHORIZED_UNCONSUMED"
    assert manifest["authority"]["token_id"] == NEW_TOKEN
    assert_logical(SRFD_REL / "srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v1_0_EACR.json")


def test_old_unmerged_pr558_token_is_not_reused():
    record = j(EACR_REL / "EACR_PR558_UNMERGED_AUTHORITY_SUPERSESSION.json")
    assert record["old_token_id"] == OLD_PR558_TOKEN
    assert record["consumed"] is False
    assert record["disposition"] == "SUPERSEDED_UNUSED_BY_EACR_SHARED_INFRASTRUCTURE_REBIND_DO_NOT_REUSE"
    assert_logical(EACR_REL / "EACR_PR558_UNMERGED_AUTHORITY_SUPERSESSION.json")


def test_v09_failure_stays_authoritative_until_eacr_g1():
    current = json_at("0515d515b261cada7daef9a9cc5ae03db9e462ad", STATE / "CURRENT_STATE_POINTER.json")
    candidate = j(STATE / "OVC_SRFDI_STATE_v0_44_WP10_V10_EACR_READY_CANDIDATE.json")
    assert current["status"] == "BLOCKED"
    assert current["failure_reason"] == "CAPACITY_EXCEEDED_EXTERNAL_BYTES"
    assert candidate["status"] == "READY_CANDIDATE_PENDING_EACR_G1"
    assert candidate["fresh_authority"]["state"] == "AUTHORIZED_UNCONSUMED"
    assert candidate["fresh_authority"]["execution_started"] is False
    assert candidate["current_authoritative_srfd_state"] == "V0_9_BLOCKED_UNTIL_EACR_G1"


def test_srfd_storage_module_is_thin_adapter_and_runner_bug_is_fixed():
    storage = (ROOT / "src/ovc/opt_b/srfd/wp10_v10_storage.py").read_text()
    runner = (ROOT / "src/ovc/opt_b/srfd/wp10_v10_runner.py").read_text()
    assert "from ovc_evidence_store import ContentAddressedArtifactStore" in storage
    assert "import gzip" not in storage
    assert "import os" not in storage
    assert "v09_root=Path(v09_root)" in runner
    assert "v09_root=Path(v09_reuse_root), source=source" not in runner


def test_eacr_rebind_qa_confirms_no_benchmark_run():
    qa = j(SRFD_REL / "srfdi-wp10-v1-0/SRFDI_WP10_V10_EACR_REBIND_QA.json")
    decision = j(SRFD_REL / "srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_OPERATOR_DECISION_v1_0_EACR.json")
    token = j(SRFD_REL / "srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_TOKEN_v1_0_EACR.json")
    assert qa["checks"]["benchmark_execution_started"] == "NO"
    assert qa["status"] == "PASS_READY_FOR_EACR_G1_REVIEW_NOT_RUN"
    assert token["state"] == "AUTHORIZED_UNCONSUMED"
    assert decision["authority_delta"]["science_delta"] == "NONE"
    assert decision["next_action"].startswith("STOP_TOKEN_UNCONSUMED")
    assert_logical(SRFD_REL / "srfdi-wp10-v1-0/SRFDI_WP10_V10_EACR_REBIND_QA.json")
    assert_logical(SRFD_REL / "srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_OPERATOR_DECISION_v1_0_EACR.json")
    assert_logical(SRFD_REL / "srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_TOKEN_v1_0_EACR.json")
