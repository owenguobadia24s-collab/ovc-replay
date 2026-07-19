from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from run_opt_d_holdout_validation import load_gzip, verify_manifest  # noqa: E402
from run_opt_d_robustness_review import MANIFEST_NAME as ROBUSTNESS_MANIFEST_NAME  # noqa: E402
from run_paper_playbook_gate import (  # noqa: E402
    MANIFEST_NAME,
    build_gate_records,
    summarize,
)


def canonical_stream_hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            digest.update(
                (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
            )
            count += 1
    return digest.hexdigest(), count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--robustness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.release_root.resolve()
    manifest = verify_manifest(root, MANIFEST_NAME)
    validation_manifest = verify_manifest(
        args.validation_root.resolve(), "OPT_D_UNTOUCHED_VALIDATION_MANIFEST.json"
    )
    robustness_manifest = verify_manifest(
        args.robustness_root.resolve(), ROBUSTNESS_MANIFEST_NAME
    )
    if manifest["validation_manifest_hash"] != validation_manifest["manifest_hash"]:
        raise ValueError("paper gate validation lineage mismatch")
    if manifest["robustness_manifest_hash"] != robustness_manifest["manifest_hash"]:
        raise ValueError("paper gate robustness lineage mismatch")
    if manifest["validation_verification_sha256"] != sha256(
        args.validation_root.resolve() / "OPT_D_UNTOUCHED_VALIDATION_VERIFICATION.json"
    ):
        raise ValueError("paper gate validation-verification binding mismatch")
    if manifest["robustness_verification_sha256"] != sha256(
        args.robustness_root.resolve() / "OPT_D_ROBUSTNESS_REVIEW_VERIFICATION.json"
    ):
        raise ValueError("paper gate robustness-verification binding mismatch")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"paper gate artifact mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    validation_rows = load_gzip(
        args.validation_root.resolve() / "opt_d_holdout_validation_ledger.jsonl.gz"
    )
    robustness_rows = load_gzip(
        args.robustness_root.resolve() / "opt_d_robustness_review_ledger.jsonl.gz"
    )
    expected_gate, expected_authorized = build_gate_records(
        validation_rows=validation_rows, robustness_rows=robustness_rows
    )
    actual_gate = load_gzip(root / "paper_playbook_gate_ledger.jsonl.gz")
    actual_authorized = load_gzip(root / "paper_playbook_authorized_registry.jsonl.gz")
    if actual_gate != expected_gate or actual_authorized != expected_authorized:
        raise ValueError("independent paper-playbook gate recomputation mismatch")
    if len(actual_gate) != 202:
        raise ValueError("paper gate batch cardinality mismatch")

    gate_hash, gate_count = canonical_stream_hash(root / "paper_playbook_gate_ledger.jsonl.gz")
    authorized_hash, authorized_count = canonical_stream_hash(
        root / "paper_playbook_authorized_registry.jsonl.gz"
    )
    expected_summary = summarize(expected_gate, expected_authorized)
    expected_summary["stream_metadata"] = {
        "gate_records": gate_count,
        "gate_canonical_jsonl_hash": gate_hash,
        "authorized_records": authorized_count,
        "authorized_canonical_jsonl_hash": authorized_hash,
    }
    if manifest["results"] != expected_summary:
        raise ValueError("paper gate summary mismatch")
    if any(row["gate_decision"] != "BLOCK" for row in actual_gate):
        raise ValueError("unexpected non-block decision in current paper gate")
    if actual_authorized:
        raise ValueError("blocked batch emitted paper-playbook authorization")
    if any(
        row["paper_execution_authority"] != "NONE"
        or row["live_execution_authority"] != "NONE"
        or row["execution_authority"] != "NONE"
        for row in actual_gate
    ):
        raise ValueError("execution authority escaped paper gate")

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(args.determinism_root.resolve(), MANIFEST_NAME)
        if other["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError("paper gate deterministic reproduction mismatch")
        determinism = {"checked": True, "manifest_hash_match": True}

    result = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": {
            "gate_rows": gate_count,
            "gate_canonical_jsonl_hash": gate_hash,
            "authorized_rows": authorized_count,
            "authorized_canonical_jsonl_hash": authorized_hash,
        },
        "determinism": determinism,
        "controls": {
            "all_202_gate_decisions_recomputed": True,
            "failure_conditions_applied_without_rescue": True,
            "no_authorization_without_all_mandatory_passes": True,
            "empty_authorized_registry_verified": True,
            "no_paper_execution_or_live_execution_authority": True,
        },
        "authority_boundary": "Independent verification of the paper-playbook authority decision only.",
    }
    (root / "PAPER_PLAYBOOK_GATE_VERIFICATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "PAPER_PLAYBOOK_GATE_VERIFICATION.md").write_text(
        "\n".join([
            "# Paper-Playbook Gate Verification",
            "",
            "**Status:** `PASS`  ",
            f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
            f"**Deterministic reproduction:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
            "",
            "All 202 decisions were independently recomputed. The authorized registry is empty, all failed frozen conditions remain blocking, and no paper-execution or live-execution authority exists.",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PASS",
        "manifest_hash": manifest["manifest_hash"],
        "gate_records": gate_count,
        "authorized_records": authorized_count,
        "determinism": determinism["checked"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
