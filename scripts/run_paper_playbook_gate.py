from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from ovc_opt_b import PAPER_PLAYBOOK_GATE_VERSION, paper_playbook_gate  # noqa: E402
from run_complete_opt_b_replay import (  # noqa: E402
    DeterministicJsonlGzipWriter,
    canonical_hash,
)
from run_opt_d_holdout_validation import load_gzip, verify_manifest  # noqa: E402
from run_opt_d_robustness_review import MANIFEST_NAME as ROBUSTNESS_MANIFEST_NAME  # noqa: E402


MANIFEST_NAME = "PAPER_PLAYBOOK_GATE_MANIFEST.json"


def build_gate_records(
    *,
    validation_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    validation_by_id = {row["hypothesis_id"]: row for row in validation_rows}
    robustness_by_id = {row["hypothesis_id"]: row for row in robustness_rows}
    if set(validation_by_id) != set(robustness_by_id):
        raise ValueError("paper gate input hypothesis sets differ")
    gate_rows = []
    authorized = []
    for robustness in robustness_rows:
        validation = validation_by_id[robustness["hypothesis_id"]]
        decision = paper_playbook_gate(validation=validation, robustness=robustness)
        core = {
            "hypothesis_id": robustness["hypothesis_id"],
            "source_story_archetype_id": robustness["source_story_archetype_id"],
            "antecedent": robustness["antecedent"],
            "expected_forward_response": robustness["expected_forward_response"],
            "validation_record_id": validation["validation_record_id"],
            "robustness_record_id": robustness["robustness_record_id"],
            "validation_disposition": validation["validation_disposition"],
            "robustness_disposition": robustness["robustness_disposition"],
            **decision,
            "gate_contract_version": PAPER_PLAYBOOK_GATE_VERSION,
            "probability_authority": "NONE",
            "edge_authority": "NONE",
            "trade_authority": "NONE",
            "execution_authority": "NONE",
        }
        record = {
            **core,
            "paper_playbook_gate_record_id": f"paper-playbook-gate:{canonical_hash(core)}",
        }
        gate_rows.append(record)
        if record["paper_playbook_authorized"]:
            authorization_core = {
                "hypothesis_id": record["hypothesis_id"],
                "paper_playbook_gate_record_id": record["paper_playbook_gate_record_id"],
                "authorization_scope": "SEPARATE_NON_LIVE_PAPER_PLAYBOOK_DRAFT_ONLY",
                "live_execution_authority": "NONE",
            }
            authorized.append({
                **authorization_core,
                "paper_playbook_authorization_id": (
                    f"paper-playbook-authorization:{canonical_hash(authorization_core)}"
                ),
            })
    return gate_rows, authorized


def summarize(gate_rows: list[dict[str, object]], authorized: list[dict[str, object]]) -> dict[str, object]:
    decisions = Counter(str(row["gate_decision"]) for row in gate_rows)
    blockers = Counter(
        str(reason) for row in gate_rows for reason in row["blocking_reasons"]
    )
    deferrals = Counter(
        str(reason) for row in gate_rows for reason in row["deferral_reasons"]
    )
    by_horizon: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in gate_rows:
        by_horizon[int(row["expected_forward_response"]["horizon_hours"])].append(row)
    return {
        "gate_status": (
            "OPEN_WITH_AUTHORIZED_PAPER_CANDIDATES"
            if authorized else "CLOSED_NO_CANDIDATE_AUTHORIZED"
        ),
        "hypotheses_gated": len(gate_rows),
        "decision_counts": {
            decision: decisions.get(decision, 0) for decision in ("PASS", "DEFER", "BLOCK")
        },
        "blocking_reason_counts": dict(sorted(blockers.items())),
        "deferral_reason_counts": dict(sorted(deferrals.items())),
        "paper_playbook_authorizations": len(authorized),
        "paper_playbooks_created": 0,
        "horizon_results": {
            str(horizon): {
                "total": len(rows),
                "pass": sum(row["gate_decision"] == "PASS" for row in rows),
                "defer": sum(row["gate_decision"] == "DEFER" for row in rows),
                "block": sum(row["gate_decision"] == "BLOCK" for row in rows),
            }
            for horizon, rows in sorted(by_horizon.items())
        },
        "paper_execution_authority": "NONE",
        "live_execution_authority": "NONE",
        "next_research_boundary": "PREREGISTERED_SEMANTIC_REFINEMENT_ON_DISCOVERY_DATA_THEN_NEW_UNTOUCHED_HOLDOUT",
    }


def write_report(output: Path, summary: dict[str, object]) -> Path:
    lines = [
        "# OVC Paper-Playbook Gate v0.1",
        "",
        f"**Gate status:** `{summary['gate_status']}`  ",
        f"**Contract:** `{PAPER_PLAYBOOK_GATE_VERSION}`  ",
        "**Paper execution / live execution authority:** `NONE`",
        "",
        "## Decision",
        "",
        f"The gate evaluated **{summary['hypotheses_gated']:,}** frozen hypotheses: "
        f"**{summary['decision_counts']['PASS']:,} PASS**, "
        f"**{summary['decision_counts']['DEFER']:,} DEFER**, and "
        f"**{summary['decision_counts']['BLOCK']:,} BLOCK**. "
        f"No paper playbook was authorized or created.",
        "",
        "| Horizon | Total | Pass | Defer | Block |",
        "|---:|---:|---:|---:|---:|",
    ]
    for horizon, row in summary["horizon_results"].items():
        lines.append(
            f"| {horizon}h | {row['total']:,} | {row['pass']:,} | "
            f"{row['defer']:,} | {row['block']:,} |"
        )
    lines.extend([
        "",
        "## Blocking evidence",
        "",
    ])
    for reason, count in summary["blocking_reason_counts"].items():
        lines.append(f"- `{reason}`: **{count:,}** hypotheses")
    lines.extend([
        "",
        "Structural recurrence is not enough for playbook translation when the same frozen antecedent and horizon produce at least as many contradictory overlap clusters as matching clusters. The leave-one-month-out review shows that this conflict is persistent rather than attributable to one calendar month.",
        "",
        "## Next boundary",
        "",
        "The approved next action is a new exploratory semantic-refinement cycle on discovery-authority data. Any revised story must be preregistered and validated on a new untouched interval. The 2025 holdout is now opened evidence and cannot be reused as untouched confirmation.",
    ])
    path = output / "OVC_PAPER_PLAYBOOK_GATE_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--robustness-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("paper-playbook gate target exists")
    output.mkdir(parents=True)

    validation_manifest = verify_manifest(
        args.validation_root.resolve(), "OPT_D_UNTOUCHED_VALIDATION_MANIFEST.json"
    )
    robustness_manifest = verify_manifest(
        args.robustness_root.resolve(), ROBUSTNESS_MANIFEST_NAME
    )
    if robustness_manifest["validation_manifest_hash"] != validation_manifest["manifest_hash"]:
        raise ValueError("paper gate robustness/validation lineage mismatch")
    validation_verification = json.loads(
        (args.validation_root.resolve() / "OPT_D_UNTOUCHED_VALIDATION_VERIFICATION.json")
        .read_text(encoding="utf-8")
    )
    robustness_verification = json.loads(
        (args.robustness_root.resolve() / "OPT_D_ROBUSTNESS_REVIEW_VERIFICATION.json")
        .read_text(encoding="utf-8")
    )
    if validation_verification["status"] != "PASS":
        raise ValueError("paper gate requires passed validation verification")
    if robustness_verification["status"] != "PASS":
        raise ValueError("paper gate requires passed robustness verification")

    validation_rows = load_gzip(
        args.validation_root.resolve() / "opt_d_holdout_validation_ledger.jsonl.gz"
    )
    robustness_rows = load_gzip(
        args.robustness_root.resolve() / "opt_d_robustness_review_ledger.jsonl.gz"
    )
    gate_rows, authorized = build_gate_records(
        validation_rows=validation_rows, robustness_rows=robustness_rows
    )
    gate_writer = DeterministicJsonlGzipWriter(output / "paper_playbook_gate_ledger.jsonl.gz")
    for row in gate_rows:
        gate_writer.write(row)
    gate_writer.close()
    authorized_writer = DeterministicJsonlGzipWriter(
        output / "paper_playbook_authorized_registry.jsonl.gz"
    )
    for row in authorized:
        authorized_writer.write(row)
    authorized_writer.close()

    summary = summarize(gate_rows, authorized)
    summary["stream_metadata"] = {
        "gate_records": gate_writer.count,
        "gate_canonical_jsonl_hash": gate_writer.canonical_jsonl_hash,
        "authorized_records": authorized_writer.count,
        "authorized_canonical_jsonl_hash": authorized_writer.canonical_jsonl_hash,
    }
    summary_path = output / "paper_playbook_gate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = write_report(output, summary)
    contract_source = ROOT / "contracts/OVC_PAPER_PLAYBOOK_GATE_CONTRACT_v0_1.md"
    contract_path = output / contract_source.name
    shutil.copy2(contract_source, contract_path)

    artifacts = []
    for path, role in (
        (gate_writer.path, "PAPER_PLAYBOOK_GATE_LEDGER"),
        (authorized_writer.path, "AUTHORIZED_PAPER_PLAYBOOK_REGISTRY"),
        (summary_path, "GATE_SUMMARY"),
        (report_path, "HUMAN_READABLE_GATE_REPORT"),
        (contract_path, "FROZEN_PAPER_PLAYBOOK_GATE_CONTRACT"),
    ):
        artifacts.append({
            "path": path.name,
            "role": role,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })
    core = {
        "release_id": "PAPER-PLAYBOOK-GATE-GBPUSD-2025-v0.1",
        "status": summary["gate_status"],
        "generated_date": "2026-07-19",
        "gate_contract_version": PAPER_PLAYBOOK_GATE_VERSION,
        "validation_manifest_hash": validation_manifest["manifest_hash"],
        "robustness_manifest_hash": robustness_manifest["manifest_hash"],
        "validation_verification_sha256": sha256(
            args.validation_root.resolve() / "OPT_D_UNTOUCHED_VALIDATION_VERIFICATION.json"
        ),
        "robustness_verification_sha256": sha256(
            args.robustness_root.resolve() / "OPT_D_ROBUSTNESS_REVIEW_VERIFICATION.json"
        ),
        "results": summary,
        "artifacts": artifacts,
        "implementation_hashes": {
            "robustness.py": sha256(ROOT / "src/ovc_opt_b/robustness.py"),
            "run_paper_playbook_gate.py": sha256(Path(__file__).resolve()),
            "validate_paper_playbook_gate.py": sha256(
                ROOT / "scripts/validate_paper_playbook_gate.py"
            ),
            "test_opt_d_robustness.py": sha256(ROOT / "tests/test_opt_d_robustness.py"),
        },
        "authority_boundary": "Authority decision for non-live paper-playbook drafting only; no paper execution or live execution authority.",
    }
    manifest = {**core, "manifest_hash": canonical_hash(core)}
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "decisions": summary["decision_counts"],
        "authorized": len(authorized),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
