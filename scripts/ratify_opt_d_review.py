from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


def verify_manifest(root: Path) -> dict[str, object]:
    manifest = json.loads((root / "OPT_D_EVIDENCE_REVIEW_MANIFEST.json").read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError("OPT-D review manifest self-hash mismatch")
    for artifact in manifest["artifacts"]:
        if sha256(root / artifact["path"]) != artifact["sha256"]:
            raise ValueError(f"review artifact mismatch: {artifact['path']}")
    return manifest


def load_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review_root = args.review_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("review ratification target exists")
    output.mkdir(parents=True)
    parent = verify_manifest(review_root)
    validation = json.loads((review_root / "OPT_D_EVIDENCE_REVIEW_VALIDATION.json").read_text(encoding="utf-8"))
    if validation["status"] != "PASS" or validation["validated_manifest_hash"] != parent["manifest_hash"]:
        raise ValueError("review release lacks matching independent validation")
    hypotheses = load_gzip(review_root / "opt_d_pending_hypothesis_register.jsonl.gz")
    if len(hypotheses) != 202:
        raise ValueError("ratification requires the complete 202-hypothesis batch")
    if any(row["operator_decision"] != "PENDING_BATCH_RATIFICATION" for row in hypotheses):
        raise ValueError("parent hypothesis decision state changed")

    writer = DeterministicJsonlGzipWriter(output / "opt_d_hypothesis_batch_ratification_ledger.jsonl.gz")
    for hypothesis in hypotheses:
        core = {
            "hypothesis_id": hypothesis["hypothesis_id"],
            "source_story_archetype_id": hypothesis["source_story_archetype_id"],
            "decision": "RATIFIED_FOR_UNTOUCHED_STRUCTURAL_VALIDATION",
            "decision_scope": "COMPLETE_202_HYPOTHESIS_BATCH",
            "decision_date": "2026-07-19",
            "review_contract_version": "OPT-D-REVIEW-0.1",
            "parent_review_manifest_hash": parent["manifest_hash"],
            "outcome_authority": "NONE",
            "execution_authority": "NONE",
        }
        writer.write({
            **core,
            "hypothesis_ratification_id": f"opt-d-hypothesis-ratification:{canonical_hash(core)}",
        })
    writer.close()

    decisions = [
        "Ratify all 202 descriptive-support hypotheses as one batch",
        "Ratify the event-time antecedent / forward-response separation",
        "Ratify exact qualitative response matching",
        "Ratify the same-antecedent-and-horizon counter-story definition",
        "Ratify 10-cluster/four-month evaluability and structural-reappearance thresholds",
        "Keep all hypotheses explicitly in-sample exploratory until untouched validation",
        "Keep 2H hypothesis authority at NONE",
        "Prohibit definition, metric, threshold or candidate changes after holdout opening",
    ]
    record = """# OPT-D-REVIEW-0.1 Batch Ratification Record

**Status:** `RATIFIED FOR UNTOUCHED STRUCTURAL VALIDATION`  
**Decision date:** `2026-07-19`  
**Hypotheses ratified:** `202`  
**Operator authorization:** `approval granted, ingest full year of data from 1 jan 2025 to 1 jan 2026 from duskoskopy, then OPT-D-VALIDATE-0.1`

## Ratified decisions

""" + "\n".join(f"- {decision}" for decision in decisions) + """

## Authority boundary

Ratification authorizes structural validation on a new sealed, non-overlapping
holdout only. It grants no probability, edge, recommendation, trade, production
or execution authority. The H1 release remains discovery evidence.
"""
    record_path = output / "OPT_D_REVIEW_0_1_BATCH_RATIFICATION_RECORD.md"
    record_path.write_text(record, encoding="utf-8")
    for name in (
        "OVC_OPT_D_EVIDENCE_REVIEW_HYPOTHESIS_CONTRACT_v0_1.md",
        "OPT_D_REVIEW_OPERATOR_RATIFICATION_CHECKLIST_v0_1.md",
    ):
        shutil.copy2(review_root / name, output / name)
    artifacts = []
    for path, role in (
        (writer.path, "HYPOTHESIS_BATCH_RATIFICATION_LEDGER"),
        (record_path, "OPERATOR_RATIFICATION_RECORD"),
        (output / "OVC_OPT_D_EVIDENCE_REVIEW_HYPOTHESIS_CONTRACT_v0_1.md", "RATIFIED_REVIEW_CONTRACT"),
        (output / "OPT_D_REVIEW_OPERATOR_RATIFICATION_CHECKLIST_v0_1.md", "SOURCE_RATIFICATION_CHECKLIST"),
    ):
        artifacts.append({
            "path": path.name,
            "role": role,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })
    manifest_core = {
        "release_id": "OPT-D-REVIEW-0.1-RATIFIED-2026-07-19",
        "status": "RATIFIED_FOR_UNTOUCHED_STRUCTURAL_VALIDATION",
        "decision_date": "2026-07-19",
        "parent_review_manifest_hash": parent["manifest_hash"],
        "parent_review_validation_status": "PASS",
        "hypotheses_ratified": len(hypotheses),
        "decision_scope": "COMPLETE_202_HYPOTHESIS_BATCH",
        "ratified_decisions": decisions,
        "holdout_requirement": "NEW_SEALED_NON_OVERLAPPING_OPT_A_RELEASE",
        "operator_authorization": "approval granted, ingest full year of data from 1 jan 2025 to 1 jan 2026 from duskoskopy, then OPT-D-VALIDATE-0.1",
        "artifacts": artifacts,
        "stream_metadata": {
            "ratification_records": writer.count,
            "ratification_stream_canonical_jsonl_hash": writer.canonical_jsonl_hash,
        },
        "authority_boundary": "Structural holdout validation only; no probability, edge, recommendation, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / "OPT_D_REVIEW_RATIFICATION_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "hypotheses_ratified": len(hypotheses),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
