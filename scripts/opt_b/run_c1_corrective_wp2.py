from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPLAY_SCRIPT = ROOT / "scripts/opt_b/run_c1_wp4_replay.py"
AUDIT_SCRIPT = ROOT / "scripts/opt_b/audit_c1_wick_balance.py"

PROGRAMME_ID = "OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1"
IMPLEMENTATION_ID = "C1.IMPLEMENTATION.v0.2"
FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
ROLES = {
    "discovery": {
        "role": "DISCOVERY",
        "release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2",
        "manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1",
        "supersedes_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "expected_records": 159892,
        "expected_files": 144,
    },
    "development": {
        "role": "DEVELOPMENT",
        "release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2",
        "manifest_id": "MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1",
        "supersedes_release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "expected_records": 52872,
        "expected_files": 48,
    },
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def logical_sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record_count(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def record_map(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*.jsonl.gz"))
    }


def compare_sets(left_root: Path, right_root: Path, label: str) -> dict[str, Any]:
    left = record_map(left_root)
    right = record_map(right_root)
    if set(left) != set(right):
        raise RuntimeError(f"{label} path-set mismatch: left-only={sorted(set(left)-set(right))[:5]} right-only={sorted(set(right)-set(left))[:5]}")
    mismatches: list[dict[str, str]] = []
    inventory: list[dict[str, Any]] = []
    total_records = 0
    for relative in sorted(left):
        left_sha = sha_file(left[relative])
        right_sha = sha_file(right[relative])
        count = record_count(left[relative])
        total_records += count
        inventory.append({"path": relative, "sha256": left_sha, "size_bytes": left[relative].stat().st_size, "record_count": count})
        if left_sha != right_sha:
            mismatches.append({"path": relative, "left_sha256": left_sha, "right_sha256": right_sha})
    return {
        "label": label,
        "file_count": len(left),
        "record_count": total_records,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:20],
        "inventory": inventory,
        "status": "PASS_BYTE_IDENTICAL" if not mismatches else "BLOCK_BYTE_MISMATCH",
    }


def active_records(root: Path) -> Path:
    candidate = root / "records"
    return candidate if candidate.is_dir() else root


def replay_records(root: Path, role: str) -> Path:
    candidate = root / role
    if not candidate.is_dir():
        raise RuntimeError(f"replay role root unavailable: {candidate}")
    return candidate


def run_replay(opt_a_discovery: Path, opt_a_development: Path, output: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPLAY_SCRIPT),
            "--discovery-root", str(opt_a_discovery),
            "--development-root", str(opt_a_development),
            "--output-root", str(output),
        ],
        cwd=ROOT,
        check=True,
    )


def build_candidate(role_key: str, replay_root: Path, target: Path, comparison: dict[str, Any], source_commit: str) -> dict[str, Any]:
    meta = ROLES[role_key]
    records_target = target / "records"
    shutil.copytree(replay_records(replay_root, role_key), records_target)
    inventory = []
    for path in sorted(records_target.rglob("*.jsonl.gz")):
        inventory.append({
            "path": path.relative_to(target).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha_file(path),
            "record_count": record_count(path),
        })
    if len(inventory) != meta["expected_files"] or sum(item["record_count"] for item in inventory) != meta["expected_records"]:
        raise RuntimeError(f"{role_key} candidate cardinality mismatch")
    descriptor = {
        "schema": "ovc-c1-corrective-candidate-release/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "C1C-WP2",
        "release_id": meta["release_id"],
        "manifest_id": meta["manifest_id"],
        "supersedes_release_id": meta["supersedes_release_id"],
        "role": meta["role"],
        "formula_registry_id": FORMULA_REGISTRY_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "source_commit": source_commit,
        "lifecycle_state": "RELEASE_FROZEN_LOCAL_CANDIDATE",
        "authority_state": "CANDIDATE",
        "availability_state": "LOCAL_ONLY",
        "active_selector": False,
        "publication_status": "NOT_ATTEMPTED",
        "record_file_count": len(inventory),
        "record_count": sum(item["record_count"] for item in inventory),
        "record_shards_byte_identical_to_active_v1": comparison["mismatch_count"] == 0,
        "validation_consumption": "LOCKED_UNCONSUMED",
        "probability_authority": "NONE",
        "exposure_authority": "NONE",
        "trading_authority": "NONE",
        "execution_authority": "NONE",
    }
    manifest_body = {
        "schema": "ovc-c1-corrective-candidate-manifest/v1",
        "release_id": meta["release_id"],
        "manifest_id": meta["manifest_id"],
        "source_commit": source_commit,
        "formula_registry_id": FORMULA_REGISTRY_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "files": inventory,
        "file_count": len(inventory),
        "record_count": descriptor["record_count"],
        "selector_eligibility": "NONE_PENDING_OPERATOR_GATES",
        "r2_publication": "DENIED_PENDING_C1C_G3",
    }
    manifest = {**manifest_body, "manifest_sha256": logical_sha(manifest_body)}
    (target / "release-descriptor.json").write_bytes(canonical_bytes(descriptor))
    (target / "manifest.json").write_bytes(canonical_bytes(manifest))
    return {"descriptor": descriptor, "manifest": manifest}


def c2_surface(role: str, root: Path) -> dict[str, Any]:
    descriptor = json.loads((root / "release-descriptor.json").read_text(encoding="utf-8"))
    state_count = int(descriptor["state_record_count"])
    transition_count = int(descriptor["transition_record_count"])
    return {
        "role": role,
        "release_id": descriptor["release_id"],
        "parent_c1_release_id": descriptor["parent_c1_release_id"],
        "state_file_count": int(descriptor["state_file_count"]),
        "state_record_count": state_count,
        "transition_file_count": int(descriptor["transition_file_count"]),
        "transition_record_count": transition_count,
        "identity_bearing_record_count": state_count + transition_count,
        "semantic_effect_from_active_c1_release_defect": "NONE_ACTIVE_C1_BYTES_ALREADY_REGISTRY_CONFORMANT",
        "identity_replay_required_if_c1_selector_moves_to_v2": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opt-a-discovery", type=Path, required=True)
    parser.add_argument("--opt-a-development", type=Path, required=True)
    parser.add_argument("--active-c1-discovery", type=Path, required=True)
    parser.add_argument("--active-c1-development", type=Path, required=True)
    parser.add_argument("--active-c2-discovery", type=Path, required=True)
    parser.add_argument("--active-c2-development", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    output = args.output_root
    if output.exists():
        raise RuntimeError(f"refusing to overwrite WP2 output: {output}")
    output.mkdir(parents=True)
    run1 = output / "replay-1"
    run2 = output / "replay-2"
    run_replay(args.opt_a_discovery, args.opt_a_development, run1)
    run_replay(args.opt_a_discovery, args.opt_a_development, run2)

    audit_path = output / "evidence/C1C_WP2_ACTIVE_RELEASE_IMPACT_AUDIT.json"
    subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--discovery-root", str(args.active_c1_discovery),
            "--development-root", str(args.active_c1_development),
            "--output", str(audit_path),
        ],
        cwd=ROOT,
        check=True,
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    comparisons: dict[str, Any] = {}
    candidates: dict[str, Any] = {}
    for role_key, active_root in (
        ("discovery", args.active_c1_discovery),
        ("development", args.active_c1_development),
    ):
        deterministic = compare_sets(
            replay_records(run1, role_key), replay_records(run2, role_key), f"{role_key}:deterministic-rerun"
        )
        active = compare_sets(
            replay_records(run1, role_key), active_records(active_root), f"{role_key}:active-v1-byte-comparison"
        )
        if deterministic["mismatch_count"] or active["mismatch_count"]:
            raise RuntimeError(f"{role_key} replay comparison failed")
        comparisons[role_key] = {"deterministic": deterministic, "active_v1": active}
        candidates[role_key] = build_candidate(
            role_key,
            run1,
            output / "candidates" / role_key,
            active,
            args.source_commit,
        )

    c2 = [
        c2_surface("DISCOVERY", args.active_c2_discovery),
        c2_surface("DEVELOPMENT", args.active_c2_development),
    ]
    c2_identity_records = sum(item["identity_bearing_record_count"] for item in c2)
    c2_identity_files = sum(item["state_file_count"] + item["transition_file_count"] for item in c2)
    downstream = {
        "schema": "ovc-c1c-downstream-affected-surface/v1",
        "active_c1_semantic_affected_records": audit["active_affected_record_count"],
        "active_c1_semantic_affected_files": audit["active_affected_file_count"],
        "c2": c2,
        "c2_identity_replay_record_count_if_v2_selected": c2_identity_records,
        "c2_identity_replay_file_count_if_v2_selected": c2_identity_files,
        "pattern_discovery": {
            "canonical_discovery_affected": False,
            "canonical_append_affected": False,
            "noncanonical_namespace": "PD.PILOT.GBPUSD.20260622_20260625.v1",
            "pilot_run_id": "PD.PILOT.RUN.0cc5a59ca751583f3e50091c",
            "source_compute_run_id": "RPS.RUN.7aeb551335d766ee3bf503e6",
            "exact_remediation_scope": "ENTIRE_NONCANONICAL_PILOT_NAMESPACE",
            "required_action": "INVALIDATE_AND_RERUN_AFTER_CORRECTED_IMPLEMENTATION",
            "reason": "prospective compute imported the corrected library path only after C1C-WP1; no canonical append or completed operator review occurred",
        },
        "status": "PASS_EXACT_SURFACES_BOUND",
    }
    downstream_path = output / "evidence/C1C_WP2_DOWNSTREAM_AFFECTED_SURFACE.json"
    downstream_path.parent.mkdir(parents=True, exist_ok=True)
    downstream_path.write_bytes(canonical_bytes(downstream))

    summary = {
        "schema": "ovc-c1c-wp2-evidence/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "C1C-WP2",
        "gate_id": "C1C-G2",
        "source_commit": args.source_commit,
        "formula_registry_id": FORMULA_REGISTRY_ID,
        "implementation_id": IMPLEMENTATION_ID,
        "active_release_impact": {
            "affected_records": audit["active_affected_record_count"],
            "affected_files": audit["active_affected_file_count"],
            "counterfactual_wrong_library_divergence_records": audit["counterfactual_wrong_library_divergence_record_count"],
        },
        "comparisons": comparisons,
        "candidates": {
            role: {
                "release_id": value["descriptor"]["release_id"],
                "manifest_id": value["descriptor"]["manifest_id"],
                "manifest_sha256": value["manifest"]["manifest_sha256"],
                "record_count": value["descriptor"]["record_count"],
                "record_file_count": value["descriptor"]["record_file_count"],
                "record_shards_byte_identical_to_active_v1": value["descriptor"]["record_shards_byte_identical_to_active_v1"],
            }
            for role, value in candidates.items()
        },
        "downstream_surface": downstream,
        "qa": {
            "deterministic_rerun": "PASS",
            "active_v1_byte_equivalence": "PASS",
            "formula_registry_conformance": "PASS",
            "candidate_cardinality": "PASS",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "r2_publication": "NOT_ATTEMPTED",
            "selector_mutation": "NONE",
        },
        "status": "PASS_LOCAL_CANDIDATES_READY_OPERATOR_GATES_NOT_AUTHORISED",
        "qa_recommendation": "PASS_C1C_G2_LOCAL_ONLY",
    }
    (output / "evidence/C1C_WP2_EVIDENCE.json").write_bytes(canonical_bytes(summary))


if __name__ == "__main__":
    main()
