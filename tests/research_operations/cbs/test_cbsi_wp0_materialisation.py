from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "registries" / "research_operations" / "cbs"
RECORDS = ROOT / "records" / "research_operations" / "cbs"
DOCS = ROOT / "docs" / "programmes" / "c2e-boundary-stability-v0-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def git_blob(path: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", path], cwd=ROOT, text=True
    ).strip()


def test_exact_plan_design_and_review_bindings() -> None:
    binding = load(REGISTRY / "CBSI_IMPLEMENTATION_PLAN_ARTIFACT_BINDING_v0_1.json")
    assert binding["design"]["sha256"] == "a4a20928f5479f34e54b5e2a1c57c19a29dfbc0ae72b69dccad4025bc03ea191"
    assert binding["artifacts"][0]["sha256"] == "fadf83075b0967168f2d354d1126d3e33d3ee8d63165a626d9cce7e4f9e56f77"
    assert binding["artifacts"][1]["sha256"] == "b86d8a31c2f905c842212435ca3fc3398ed0988bf800f6cdf637e20156d72a8c"
    assert binding["artifacts"][1]["byte_state"] == "VERIFIED_ONCE_UNBOUND"

    external = os.environ.get("OVC_EXTERNAL_ARTIFACT_ROOT")
    if external:
        root = Path(external) / "research-operations" / "cbs" / "authority"
        assert sha256(root / binding["design"]["filename"]) == binding["design"]["sha256"]
        assert sha256(root / binding["artifacts"][0]["name"]) == binding["artifacts"][0]["sha256"]


def test_packet_graph_uses_only_ratified_packet_and_gate_ids() -> None:
    graph = load(REGISTRY / "CBSI_PACKET_GATE_REGISTRY_v0_1.json")
    packet_ids = [packet["packet_id"] for packet in graph["packets"]]
    assert packet_ids == [
        "CBSI-WP0", "CBSI-WP1", "CBSI-WP2", "CBSI-WP3", "CBSI-WP4",
        "CBSI-WP5", "CBSI-WP6", "CBSI-WP7", "CBSI-WP8", "CBSI-WP9",
        "CBSI-WP10", "CBSI-WP11", "CBSI-WP12A", "CBSI-WP12B",
        "CBSI-WP13A", "CBSI-WP13B",
    ]
    assert {p["gate_after"] for p in graph["packets"] if p["gate_after"]} >= {
        "CBSI-G0", "CBSI-G1-SYNTH", "CBSI-G2-ALG", "CBSI-GREAL-DEV",
        "CBSI-GR5-FREEZE", "CBSI-GR6-REPL", "CBSI-GR7-C2E-PACK",
    }


def test_source_matrix_blob_bindings_are_exact() -> None:
    matrix = load(REGISTRY / "CBSI_SOURCE_REUSE_SUPERSESSION_MATRIX_v0_1.json")
    assert matrix["baseline_main"] == "c1bc6e32746fbf37cb9f8e6d053401092d0a44d4"
    assert matrix["baseline_tree"] == "d66c6d3066e94ba5b51073a499809cba1678f5d2"
    for source in matrix["sources"]:
        assert git_blob(source["path"]) == source["blob_sha"]
    assert matrix["blockers"] == []


def test_current_authority_preserves_pack_envelope_and_denials() -> None:
    current = load(RECORDS / "CBSI_AUTHORITY_CURRENTNESS_MANIFEST_v0_1.json")
    assert current["status"] == "PASS"
    assert current["c2e"]["pack_id"] == "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
    assert current["c2e"]["pack_sha256"] == "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
    assert current["market_envelope"]["validation"] == "LOCKED_UNCONSUMED"
    decision = load(DOCS / "implementation" / "CBSI_G0_OPERATOR_DECISION_v0_1.json")
    assert "DECISION_BEARING_REAL_SOURCE_DEVELOPMENT" in decision["explicit_non_grants"]
    assert "C2E_BOUNDARY_PACK_SELECTION_REPLACEMENT_OR_ACTIVATION" in decision["explicit_non_grants"]


def test_exposure_is_complete_and_never_claimed_blind() -> None:
    exposure = load(RECORDS / "CBSI_PRE_PLAN_EXPOSURE_MANIFEST_v0_1.json")
    ids = {entry["id"] for entry in exposure["entries"]}
    assert {"CBS-R0-LAB", "CBS-R1-B0-RESULT", "CBS-R1-B1-RESULT", "CBS-R1-B2-RESULT", "CBS-R1-B3-RESULT", "CBS-R3-LAB-CONSTITUTION", "CBS-R4-LAB-CONSTITUTION", "CBS-R5-LAB-READINESS", "CBS-R5-LAB-SEARCH-EXPOSURE", "CBS-R5-LAB-REPLICATION-RESERVATION"} <= ids
    assert any(entry["byte_state"] == "KNOWN_EXPOSURE_UNBOUND" for entry in exposure["entries"])
    assert exposure["claim_effect"] == "NO_ENTRY_IS_UNTOUCHED_CONFIRMATION"


def test_g2_reviewer_is_blocking_and_cannot_be_implementation_author() -> None:
    reviewer = load(REGISTRY / "CBSI_G2_ALG_REVIEWER_BINDING_REQUIREMENT_v0_1.json")
    assert reviewer["status"] == "REQUIRED_UNBOUND_AT_WP0"
    assert reviewer["blocking"] is True
    assert reviewer["self_certification"] == "FORBIDDEN"


def test_programme_state_advances_only_to_wp1() -> None:
    state = load(RECORDS / "CBSI_PROGRAMME_STATE_v0_1.json")
    assert state["packet_id"] == "CBSI-WP0"
    assert state["next_packet"] == "CBSI-WP1"
    assert state["real_source_development"] == "DENIED"
    assert state["c2e_owner_state"] == "READ_ONLY_UNCHANGED"


def test_wp0_vit_authority_and_dependency_frontier_are_canonical() -> None:
    wp0 = DOCS / "wp0"
    authority = load(wp0 / "CBSI_WP0_VIT_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(wp0 / "CBSI_WP0_VIT_DEPENDENCY_FRONTIER_v0_1.json")
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert authority["payload"]["authority_class"] == "AUTO_EXECUTABLE_RECORDED_OPERATOR_PASS_MATERIALISATION"
    assert "NO_REAL_SOURCE_DEVELOPMENT_BEFORE_CBSI_GREAL_DEV_PASS" in authority["payload"]["retained_denials"]
