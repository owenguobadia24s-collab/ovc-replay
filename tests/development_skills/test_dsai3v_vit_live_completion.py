from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_live_completion import record_live_completion
from ovc.development.skills.vit_routing import build_vit_lineage_record, validate_vit_lineage_record
from ovc_evidence_store.external_root import EXTERNAL_ROOT_ENV, EvidenceStoreError


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "vit-completion@example.invalid")
    _git(repo, "config", "user.name", "VIT Completion Test")
    target = repo / "payload.txt"
    target.write_text("base\n", encoding="utf-8")
    _git(repo, "add", "payload.txt")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    target.write_text("result\n", encoding="utf-8")
    _git(repo, "add", "payload.txt")
    _git(repo, "commit", "-qm", "result")
    head = _git(repo, "rev-parse", "HEAD")
    target.write_text("different\n", encoding="utf-8")
    _git(repo, "add", "payload.txt")
    _git(repo, "commit", "-qm", "different")
    different = _git(repo, "rev-parse", "HEAD")
    return repo, base, head, different


def _lineage(repo: Path, base: str, head: str) -> dict[str, object]:
    base_tree = _git(repo, "rev-parse", f"{base}^{{tree}}")
    head_tree = _git(repo, "rev-parse", f"{head}^{{tree}}")
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "OVC-TEST-PROGRAMME",
        "packet_id": "TEST-PACKET",
        "logical_changes": [
            {"op": "MODIFY", "path": "payload.txt", "blob_sha": "a" * 40, "mode": "100644"}
        ],
        "authority_manifest_id": "a" * 64,
        "dependency_frontier_id": "b" * 64,
        "completion_transition": {"status": "COMPLETED", "next_packet": "NEXT-PACKET"},
    }
    return build_vit_lineage_record(
        programme_id="OVC-TEST-PROGRAMME",
        packet_id="TEST-PACKET",
        pip_identity_payload=pip,
        train_generation_id="TEST-TRAIN",
        ordinal=7,
        predecessor_tree_sha=base_tree,
        result_tree_sha=head_tree,
        apply_profile="INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1",
    )


def _record(tmp_path: Path, *, observed: str | None = None):
    repo, base, head, different = _repo(tmp_path)
    lineage = _lineage(repo, base, head)
    external = tmp_path / "external"
    result = record_live_completion(
        repo,
        lineage=lineage,
        predecessor_commit=base,
        observed_commit=observed or head,
        implementation_ref="PR#TEST",
        qa_ref="qa/test.json",
        gate_decision_ref="gate/test.json",
        assurance_frontier_id="ASSURANCE-TEST",
        environ={EXTERNAL_ROOT_ENV: str(external)},
    )
    return repo, base, head, different, lineage, external, result


def test_new_vit_lineage_carries_exact_integration_ticket() -> None:
    # Tree identities only need to be exact-shaped for the lineage identity test.
    lineage = build_vit_lineage_record(
        programme_id="P",
        packet_id="K",
        pip_identity_payload={
            "schema_version": "packet-integration-payload/v0.1",
            "programme_id": "P",
            "packet_id": "K",
            "logical_changes": [{"op": "ADD", "path": "x", "blob_sha": "a" * 40, "mode": "100644"}],
            "authority_manifest_id": "a" * 64,
            "dependency_frontier_id": "b" * 64,
            "completion_transition": {"status": "COMPLETED"},
        },
        train_generation_id="TRAIN",
        ordinal=3,
        predecessor_tree_sha="c" * 40,
        result_tree_sha="d" * 40,
        apply_profile="PROFILE",
    )
    validated = validate_vit_lineage_record(lineage)
    assert validated.ticket_id == lineage["ticket_id"]
    assert lineage["integration_ticket"]["payload_id"] == lineage["pip_id"]
    assert lineage["integration_ticket"]["admitted_sequence"] == 3


def test_live_completion_persists_materialisation_completion_devobs_and_attachment(tmp_path: Path) -> None:
    _, _, _, _, _, external, result = _record(tmp_path)
    store = external / "receipts" / "development" / "dsai3v"
    files = sorted(store.glob("*.json"))
    assert len(files) == 4
    assert result.exact_tree_equal is True
    assert result.observed_tree == result.expected_result_tree
    devobs = json.loads((store / f"{result.development_latency_receipt_id}.json").read_text(encoding="utf-8"))
    assert devobs["latency"]["status"] == "UNAVAILABLE"
    assert devobs["vit"]["exact_tree_equal_count"] == 1
    assert devobs["siq"]["receipt_count"] == 0
    assert devobs["evidence_rule"] == "OBSERVED_FIELDS_ONLY_NO_UNOBSERVED_LATENCY_OR_EXECUTION_INFERENCE"


def test_live_completion_retry_is_idempotent(tmp_path: Path) -> None:
    repo, base, head, _, lineage, external, first = _record(tmp_path)
    second = record_live_completion(
        repo,
        lineage=lineage,
        predecessor_commit=base,
        observed_commit=head,
        implementation_ref="PR#TEST",
        qa_ref="qa/test.json",
        gate_decision_ref="gate/test.json",
        assurance_frontier_id="ASSURANCE-TEST",
        environ={EXTERNAL_ROOT_ENV: str(external)},
    )
    assert second == first
    assert len(list((external / "receipts" / "development" / "dsai3v").glob("*.json"))) == 4


def test_historical_lineage_without_ticket_fails_closed_instead_of_inventing_identity(tmp_path: Path) -> None:
    repo, base, head, _, lineage, external, _ = _record(tmp_path)
    lineage = dict(lineage)
    lineage.pop("integration_ticket")
    lineage.pop("ticket_id")
    with pytest.raises(VitContractError, match="VIT_COMPLETION_TICKET_ID_MISSING"):
        record_live_completion(
            repo,
            lineage=lineage,
            predecessor_commit=base,
            observed_commit=head,
            implementation_ref="PR#TEST",
            qa_ref="qa/test.json",
            gate_decision_ref="gate/test.json",
            assurance_frontier_id="ASSURANCE-TEST",
            environ={EXTERNAL_ROOT_ENV: str(external)},
        )


def test_post_write_tree_mismatch_never_becomes_completion(tmp_path: Path) -> None:
    repo, base, head, different = _repo(tmp_path)
    lineage = _lineage(repo, base, head)
    external = tmp_path / "external"
    with pytest.raises(VitContractError, match="POST_WRITE_TREE_MISMATCH"):
        record_live_completion(
            repo,
            lineage=lineage,
            predecessor_commit=base,
            observed_commit=different,
            implementation_ref="PR#TEST",
            qa_ref="qa/test.json",
            gate_decision_ref="gate/test.json",
            assurance_frontier_id="ASSURANCE-TEST",
            environ={EXTERNAL_ROOT_ENV: str(external)},
        )
    store = external / "receipts" / "development" / "dsai3v"
    assert not store.exists() or not list(store.glob("*.json"))


def test_receipt_store_cannot_be_redirected_inside_repository(tmp_path: Path) -> None:
    repo, base, head, _ = _repo(tmp_path)
    lineage = _lineage(repo, base, head)
    with pytest.raises(EvidenceStoreError):
        record_live_completion(
            repo,
            lineage=lineage,
            predecessor_commit=base,
            observed_commit=head,
            implementation_ref="PR#TEST",
            qa_ref="qa/test.json",
            gate_decision_ref="gate/test.json",
            assurance_frontier_id="ASSURANCE-TEST",
            environ={EXTERNAL_ROOT_ENV: str(repo / "receipts")},
        )
