from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_RUN_ID = 30212281089
SOURCE_COMMIT = "1d72d2332e71639e7eee42bef96357e4640d4fb8"
CANDIDATE_TREE_SHA256 = "f15ad152405708bca09e0255af6de69a4a54051e6f0f9e2128cd0c2944bf60fd"
SOURCE_REPLAY_ARTIFACT_ID = 8634383302
SOURCE_REPLAY_ARTIFACT_SHA256 = "b8f993f733aed75e488aa60883f00a53596c15e5cd6c14edb787fc3bc12df62f"

ARTIFACTS = {
    "DISCOVERY": {
        "id": 8634803012,
        "name": "c2-opt-b-c2-gbpusd-discovery-2021-2023-v1-frozen-candidate",
        "digest": "sha256:e92853173779ed8a34df6e96d0472e0f88528aee4c84c094255e4a012b4aad6d",
    },
    "DEVELOPMENT": {
        "id": 8634803579,
        "name": "c2-opt-b-c2-gbpusd-development-2024-v1-frozen-candidate",
        "digest": "sha256:708f53afdb75c9561a30ac4290fcf9a184adb1a0925962d2fe10e577ff3cdf63",
    },
    "GATE_PACKET": {
        "id": 8634803684,
        "name": "c2-g5-candidate-freeze-gate-packet",
        "digest": "sha256:667aa5a51ea38bb29d9c76780c69b4dbbcee7c4fc137f87dece9f35c04b06b3f",
    },
}

EXPECTED: dict[str, dict[str, Any]] = {
    "DISCOVERY": {
        "release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        "manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1",
        "manifest_sha256": "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33",
        "manifest_file_sha256": "d3a8184a8f890ea0c57882fa37d5ea726af2a799b2db0063489cb58a157dba2f",
        "parent_opt_a_release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "parent_opt_a_manifest_id": "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        "parent_opt_a_manifest_sha256": "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
        "parent_c1_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "parent_c1_manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1",
        "parent_c1_manifest_sha256": "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        "state_file_count": 6,
        "transition_file_count": 6,
        "state_record_count": 303_856,
        "transition_record_count": 245_752,
        "manifest_bound_file_count": 18,
        "manifest_bound_bytes": 659_484_886,
    },
    "DEVELOPMENT": {
        "release_id": "OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1",
        "manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1",
        "manifest_sha256": "8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e",
        "manifest_file_sha256": "79733b9aff7d290a853ae38d174974876b4cb70d4ead6e62548839bf6a923750",
        "parent_opt_a_release_id": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
        "parent_opt_a_manifest_id": "MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
        "parent_opt_a_manifest_sha256": "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
        "parent_c1_release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "parent_c1_manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1",
        "parent_c1_manifest_sha256": "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        "state_file_count": 6,
        "transition_file_count": 6,
        "state_record_count": 100_578,
        "transition_record_count": 78_158,
        "manifest_bound_file_count": 18,
        "manifest_bound_bytes": 213_382_716,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise SystemExit(f"{label}: expected {expected!r}, got {actual!r}")


def verify_repository_binding(repo_root: Path, manifest: dict[str, Any], role: str) -> None:
    for field in ("contract_hashes", "schema_hashes", "registry_hashes"):
        mapping = manifest.get(field)
        if not isinstance(mapping, dict) or not mapping:
            raise SystemExit(f"{role}: missing {field}")
        for rel, expected_hash in sorted(mapping.items()):
            path = repo_root / rel
            if not path.is_file() or path.is_symlink():
                raise SystemExit(f"{role}: missing repository binding {rel}")
            require(sha256(path), expected_hash, f"{role}: repository binding {rel}")
    parameter_pack = repo_root / "registries/opt_b/c2/C2_PARAMETER_PACK_v0_1.yaml"
    require(sha256(parameter_pack), manifest.get("parameter_pack_hash"), f"{role}: parameter pack")


def verify_source_binding(root: Path, role: str) -> None:
    source = load_json(root / "source/C2_G4_SOURCE_BINDING.json")
    required = {
        "schema": "ovc-c2-g5-source-binding/v1",
        "artifact_id": SOURCE_REPLAY_ARTIFACT_ID,
        "artifact_name": "c2-g4-exact-parent-replay-output",
        "artifact_archive_sha256": SOURCE_REPLAY_ARTIFACT_SHA256,
        "workflow_run_id": 30210057332,
        "workflow_commit": "4fb06b4d2b13bdf737446cb619e548eb987aeab1",
        "replay_receipt_sha256": "27aac06a35a56518eab67027272238c7bd265161b552823b5ab59d0547d13018",
        "intake_receipt_sha256": "4d519786ce8cc138a88924d1d2ec7de37caabad2ea83e021b403f91c4266d21b",
    }
    for key, value in required.items():
        require(source.get(key), value, f"{role}: source binding {key}")
    require(sha256(root / "source/WP5_LOCAL_REPLAY_RECEIPT.json"), required["replay_receipt_sha256"], f"{role}: replay receipt")
    require(sha256(root / "source/WP5_CANONICAL_INTAKE_RECEIPT.json"), required["intake_receipt_sha256"], f"{role}: intake receipt")


def verify_qa(root: Path, expected: dict[str, Any], role: str) -> None:
    summary = load_json(root / "qa/C2_G5_QA_SUMMARY.json")
    ledger = load_json(root / "qa/C2_G5_ISSUE_LEDGER.json")
    require(summary.get("schema"), "ovc-c2-g5-qa-summary/v1", f"{role}: QA schema")
    require(summary.get("status"), "PASS", f"{role}: QA status")
    require(summary.get("release_id"), expected["release_id"], f"{role}: QA release")
    require(summary.get("blocking_issues"), 0, f"{role}: blocking issues")
    require(summary.get("unresolved_issues"), 0, f"{role}: unresolved issues")
    require(summary.get("validation_consumption"), "LOCKED_UNCONSUMED", f"{role}: validation")
    for field in ("publication", "selector", "activation"):
        require(summary.get(field), "NONE", f"{role}: QA {field}")
    checks = summary.get("checks")
    if not isinstance(checks, list) or len(checks) != 10 or any(item.get("status") != "PASS" for item in checks):
        raise SystemExit(f"{role}: incomplete QA check set")
    require(ledger.get("schema"), "ovc-c2-g5-issue-ledger/v1", f"{role}: issue schema")
    require(ledger.get("issue_count"), 0, f"{role}: issue count")
    require(ledger.get("open_issue_count"), 0, f"{role}: open issue count")
    require(ledger.get("issues"), [], f"{role}: issue ledger")


def verify_release(root: Path, role: str, repo_root: Path) -> dict[str, Any]:
    expected = EXPECTED[role]
    manifest_path = root / "manifest.json"
    descriptor_path = root / "release-descriptor.json"
    if not manifest_path.is_file() or not descriptor_path.is_file():
        raise SystemExit(f"{role}: manifest or descriptor missing")
    require(sha256(manifest_path), expected["manifest_file_sha256"], f"{role}: manifest file SHA-256")
    manifest = load_json(manifest_path)
    manifest_copy = dict(manifest)
    self_hash = manifest_copy.pop("manifest_sha256", None)
    require(self_hash, expected["manifest_sha256"], f"{role}: manifest identity")
    require(hashlib.sha256(canonical_bytes(manifest_copy)).hexdigest(), self_hash, f"{role}: manifest self-hash")
    require(manifest.get("release_id"), expected["release_id"], f"{role}: manifest release")
    require(manifest.get("manifest_id"), expected["manifest_id"], f"{role}: manifest ID")
    require(manifest.get("total_bytes"), expected["manifest_bound_bytes"], f"{role}: manifest bytes")

    parent_map = {item.get("layer"): item for item in manifest.get("parent_manifests", [])}
    for layer, prefix in (("OPT-A", "parent_opt_a"), ("OPT-B.C1", "parent_c1")):
        parent = parent_map.get(layer)
        if not parent:
            raise SystemExit(f"{role}: missing {layer} parent")
        require(parent.get("release_id"), expected[f"{prefix}_release_id"], f"{role}: {layer} release")
        require(parent.get("manifest_id"), expected[f"{prefix}_manifest_id"], f"{role}: {layer} manifest")
        require(parent.get("manifest_sha256"), expected[f"{prefix}_manifest_sha256"], f"{role}: {layer} hash")

    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != expected["manifest_bound_file_count"]:
        raise SystemExit(f"{role}: manifest inventory count mismatch")
    if [item.get("path") for item in files] != sorted(item.get("path") for item in files):
        raise SystemExit(f"{role}: manifest inventory not canonical")
    if len({item.get("path") for item in files}) != len(files):
        raise SystemExit(f"{role}: duplicate manifest path")

    total_bytes = 0
    state_files = transition_files = state_records = transition_records = 0
    expected_paths = {"manifest.json"}
    for item in files:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise SystemExit(f"{role}: unsafe path {rel}")
        path = root / rel
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"{role}: missing/linked file {rel}")
        require(path.stat().st_size, item.get("size_bytes"), f"{role}: size {rel}")
        require(sha256(path), item.get("sha256"), f"{role}: hash {rel}")
        total_bytes += path.stat().st_size
        expected_paths.add(rel.as_posix())
        if item.get("record_type") == "STATE":
            state_files += 1
            state_records += int(item.get("record_count", 0))
        elif item.get("record_type") == "TRANSITION":
            transition_files += 1
            transition_records += int(item.get("record_count", 0))
    actual_paths = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    require(actual_paths, expected_paths, f"{role}: complete inventory")
    require(total_bytes, expected["manifest_bound_bytes"], f"{role}: verified bytes")
    require(state_files, expected["state_file_count"], f"{role}: state files")
    require(transition_files, expected["transition_file_count"], f"{role}: transition files")
    require(state_records, expected["state_record_count"], f"{role}: state records")
    require(transition_records, expected["transition_record_count"], f"{role}: transition records")

    descriptor = load_json(descriptor_path)
    descriptor_required = {
        "schema": "ovc-c2-release-descriptor/v1",
        "release_id": expected["release_id"],
        "role": role,
        "lifecycle_state": "RELEASE_FROZEN",
        "authority_state": "CANDIDATE",
        "availability_state": "LOCAL_ONLY",
        "publication_status": "NOT_ATTEMPTED",
        "active_selector": False,
        "selector_state": "NONE",
        "rollback_target": "NONE_C1_ONLY",
        "source_replay_artifact_id": SOURCE_REPLAY_ARTIFACT_ID,
        "source_replay_workflow_run_id": 30210057332,
        "validation_consumption": "LOCKED_UNCONSUMED",
        "probability_authority": "NONE",
        "exposure_authority": "NONE",
        "trading_authority": "NONE",
        "execution_authority": "NONE",
        "state_file_count": expected["state_file_count"],
        "transition_file_count": expected["transition_file_count"],
        "state_record_count": expected["state_record_count"],
        "transition_record_count": expected["transition_record_count"],
        "rejected_record_count": 0,
    }
    for key, value in descriptor_required.items():
        require(descriptor.get(key), value, f"{role}: descriptor {key}")
    for prefix in ("parent_opt_a", "parent_c1"):
        for suffix in ("release_id", "manifest_id", "manifest_sha256"):
            key = f"{prefix}_{suffix}"
            require(descriptor.get(key), expected[key], f"{role}: descriptor {key}")

    verify_source_binding(root, role)
    verify_qa(root, expected, role)
    verify_repository_binding(repo_root, manifest, role)
    return {
        "role": role,
        "release_id": expected["release_id"],
        "manifest_id": expected["manifest_id"],
        "manifest_sha256": expected["manifest_sha256"],
        "manifest_file_sha256": expected["manifest_file_sha256"],
        "candidate_artifact": ARTIFACTS[role],
        "state_file_count": state_files,
        "transition_file_count": transition_files,
        "state_record_count": state_records,
        "transition_record_count": transition_records,
        "manifest_bound_file_count": len(files),
        "verified_payload_bytes": total_bytes,
        "remote_prefix": f"canonical/releases/{expected['release_id']}/{expected['manifest_id']}/",
        "remote_collision_preflight": "PASS_ABSENT",
    }


def verify_gate_packet(path: Path) -> None:
    gate = load_json(path)
    require(gate.get("decision"), "PASS_LOCAL_CANDIDATE_RELEASE_FROZEN", "C2-G5 gate decision")
    verification = gate.get("verification", {})
    require(verification.get("candidate_tree_sha256"), CANDIDATE_TREE_SHA256, "candidate tree")
    require(verification.get("full_byte_local_verification"), "PASS", "C2-G5 byte verification")
    require(verification.get("blocking_qa_issues"), 0, "C2-G5 blocking issues")
    require(verification.get("unresolved_qa_issues"), 0, "C2-G5 unresolved issues")
    authority = gate.get("authority_delta", {})
    for field in ("publication", "selector", "activation"):
        require(authority.get(field), "NONE", f"C2-G5 {field}")
    require(authority.get("validation_consumption"), "LOCKED_UNCONSUMED", "C2-G5 validation")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery-root", type=Path, required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--source-gate-packet", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--artifact-metadata", type=Path, required=True)
    parser.add_argument("--remote-collision-state", choices=["PASS_ABSENT"], required=True)
    parser.add_argument("--operator-approval", choices=["APPROVE_EXACT_R2_PUBLICATION_ONLY"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metadata = load_json(args.artifact_metadata)
    for role, expected in ARTIFACTS.items():
        item = metadata.get(role)
        if not item:
            raise SystemExit(f"missing artifact metadata: {role}")
        for key in ("id", "name", "digest"):
            require(item.get(key), expected[key], f"artifact {role} {key}")

    verify_gate_packet(args.source_gate_packet)
    releases = [
        verify_release(args.discovery_root, "DISCOVERY", args.repo_root),
        verify_release(args.development_root, "DEVELOPMENT", args.repo_root),
    ]
    receipt = {
        "schema": "ovc-c2-publication-readiness-receipt/v1",
        "gate_id": "C2-PUB-G0",
        "decision": "PASS_PUBLICATION_READY_OPERATOR_APPROVED_EXACT_RELEASES_ONLY",
        "source_candidate_freeze": {
            "workflow_run_id": SOURCE_RUN_ID,
            "source_commit": SOURCE_COMMIT,
            "candidate_tree_sha256": CANDIDATE_TREE_SHA256,
            "gate_packet_artifact": ARTIFACTS["GATE_PACKET"],
        },
        "verification": {
            "artifact_identity": "PASS",
            "manifest_self_hashes": "PASS",
            "complete_inventory_binding": "PASS",
            "full_byte_local_verification": "PASS",
            "repository_contract_schema_registry_binding": "PASS",
            "exact_opt_a_and_c1_parent_binding": "PASS",
            "qa_issue_closure": "PASS_ZERO_OPEN_OR_UNRESOLVED",
            "remote_collision_preflight": args.remote_collision_state,
            "candidate_tree_sha256": CANDIDATE_TREE_SHA256,
        },
        "releases": releases,
        "totals": {
            "release_count": 2,
            "manifest_bound_file_count": sum(item["manifest_bound_file_count"] for item in releases),
            "state_file_count": sum(item["state_file_count"] for item in releases),
            "transition_file_count": sum(item["transition_file_count"] for item in releases),
            "state_record_count": sum(item["state_record_count"] for item in releases),
            "transition_record_count": sum(item["transition_record_count"] for item in releases),
            "verified_payload_bytes": sum(item["verified_payload_bytes"] for item in releases),
        },
        "operator_approval": {
            "decision": args.operator_approval,
            "publication_scope": "EXACT_DISCOVERY_AND_DEVELOPMENT_RELEASES_ONLY",
            "publication_method": "PAYLOAD_FIRST_MANIFEST_LAST_IMMUTABLE_R2",
            "required_post_write_verification": "FULL_REMOTE_BYTE_READBACK",
        },
        "authority": {
            "r2_publication": "AUTHORISED_EXACT_RELEASES_ONLY",
            "remote_write_executed": False,
            "selector": "NONE",
            "activation": "NONE",
            "direct_active_discovery": "DENIED_PENDING_REMOTE_VERIFICATION_AND_SEPARATE_SELECTOR_RETIREMENT_TRANSACTION",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "c2e": "DEFERRED",
            "c2_5": "DEFERRED",
            "c3": "DEFERRED",
            "opt_c": "NONE",
            "opt_d": "NONE",
            "probability": "NONE",
            "exposure": "NONE",
            "trading": "NONE",
            "execution": "NONE",
        },
        "next_boundary": "C2_R2_PUBLICATION_AND_FULL_REMOTE_VERIFICATION_EXACT_RELEASES_ONLY",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(receipt))


if __name__ == "__main__":
    main()
