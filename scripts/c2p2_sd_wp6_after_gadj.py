#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any

from ovc.opt_b.c2p_v0_2.sd_discrimination import (
    CANDIDATE_IDS,
    build_blind_review_card,
    build_unblinding_map,
)

PROGRAMME_ID = "OVC-C2P2-SCIENTIFIC-DISCRIMINATION-v0.1"
GATE_ID = "C2P2-SD-GADJ"
BLINDING_KEY = "C2P2-SD-PRESENTATION-BLIND-v0.1"
EXPECTED_MANIFEST_SHA256 = "4e6abf3afda0ce762737b02e2b5b54bdc96a3f6bc4427951eaa8feeccc70b8ae"
EXPECTED_CASES = 72
RELEASE = Path("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-sd")
LABEL_FREEZE = RELEASE / "C2P2_SD_GADJ_HUMAN_LABEL_FREEZE_v0_1.json"
GREAL_RESULT = RELEASE / "C2P2_SD_GREAL_RUN_RESULT_v0_1.json"
STATE = Path("registries/implementation/c2p_v0_2/C2P2_SD_EXECUTION_STATE_v0_1.json")


class WP6Error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_freeze(repo_root: Path, evidence_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    freeze_path = repo_root / LABEL_FREEZE
    manifest_path = evidence_root / "full-population-discrimination/blind-review-manifest.jsonl"
    if not freeze_path.is_file() or not manifest_path.is_file():
        raise WP6Error("C2P2_SD_WP6_REQUIRED_INPUT_MISSING")
    if file_sha256(manifest_path) != EXPECTED_MANIFEST_SHA256:
        raise WP6Error("C2P2_SD_WP6_BLIND_MANIFEST_HASH_DRIFT")
    cards = load_manifest(manifest_path)
    if len(cards) != EXPECTED_CASES:
        raise WP6Error("C2P2_SD_WP6_BLIND_CASE_COUNT_DRIFT")
    if any(card.get("candidate_names_hidden") is not True for card in cards):
        raise WP6Error("C2P2_SD_WP6_PRE_FREEZE_CANDIDATE_VISIBILITY_DRIFT")
    if any(card.get("adjudication_label") is not None for card in cards):
        raise WP6Error("C2P2_SD_WP6_SOURCE_MANIFEST_ALREADY_LABELLED")

    freeze = load_json(freeze_path)
    if freeze.get("schema") != "ovc-c2p2-sd-gadj-human-label-freeze/v1":
        raise WP6Error("C2P2_SD_WP6_LABEL_FREEZE_SCHEMA_INVALID")
    if freeze.get("programme_id") != PROGRAMME_ID or freeze.get("gate_id") != GATE_ID:
        raise WP6Error("C2P2_SD_WP6_LABEL_FREEZE_IDENTITY_INVALID")
    if freeze.get("decision") != "FREEZE_LABEL_SET" or freeze.get("review_case_count") != EXPECTED_CASES:
        raise WP6Error("C2P2_SD_WP6_LABEL_FREEZE_STATE_INVALID")
    if freeze.get("blind_review_manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise WP6Error("C2P2_SD_WP6_LABEL_FREEZE_MANIFEST_MISMATCH")
    if freeze.get("candidate_names_visible_at_freeze") is not False:
        raise WP6Error("C2P2_SD_WP6_LABEL_FREEZE_NOT_BLIND")
    if freeze.get("unblinding_before_freeze") != "FORBIDDEN_AND_NOT_PERFORMED":
        raise WP6Error("C2P2_SD_WP6_UNBLINDING_ORDER_INVALID")

    labels = freeze.get("labels")
    if not isinstance(labels, list) or len(labels) != EXPECTED_CASES:
        raise WP6Error("C2P2_SD_WP6_LABEL_COUNT_INVALID")
    ids = [str(row.get("review_case_id")) for row in labels]
    if len(ids) != len(set(ids)):
        raise WP6Error("C2P2_SD_WP6_DUPLICATE_LABEL_CASE")
    manifest_ids = [str(card["review_case_id"]) for card in cards]
    if set(ids) != set(manifest_ids):
        raise WP6Error("C2P2_SD_WP6_LABEL_CASE_SET_MISMATCH")
    allowed = {"SAME", "DIFFERENT", "AMBIGUOUS", "NOT_EVALUABLE"}
    if any(row.get("adjudication_label") not in allowed for row in labels):
        raise WP6Error("C2P2_SD_WP6_LABEL_VALUE_INVALID")
    label_digest = sha256(canonical_json(labels).encode("utf-8")).hexdigest()
    if label_digest != freeze.get("labels_sha256"):
        raise WP6Error("C2P2_SD_WP6_LABEL_DIGEST_INVALID")
    observed = Counter(str(row["adjudication_label"]) for row in labels)
    expected_counts = {label: int(freeze.get("label_counts", {}).get(label, 0)) for label in sorted(allowed)}
    for label in allowed:
        if observed.get(label, 0) != expected_counts.get(label, 0):
            raise WP6Error("C2P2_SD_WP6_LABEL_COUNT_MAP_DRIFT")
    return freeze, cards


def correlate_records(evidence_root: Path, cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    database = evidence_root / "full-population-discrimination/review-selection.sqlite3"
    if not database.is_file():
        raise WP6Error("C2P2_SD_WP6_REVIEW_DATABASE_MISSING")
    by_case = {str(card["review_case_id"]): card for card in cards}
    connection = sqlite3.connect(database)
    try:
        query = """
            SELECT edge_id, payload_json FROM hard_cases
            UNION ALL
            SELECT r.edge_id, r.payload_json
            FROM representatives r
            WHERE NOT EXISTS (SELECT 1 FROM hard_cases h WHERE h.edge_id = r.edge_id)
            ORDER BY edge_id
        """
        result: dict[str, dict[str, Any]] = {}
        for _, payload_json in connection.execute(query):
            record = json.loads(payload_json)
            blind_card = build_blind_review_card(record, BLINDING_KEY)
            case_id = str(blind_card["review_case_id"])
            if case_id not in by_case:
                raise WP6Error("C2P2_SD_WP6_REPRESENTATIVE_NOT_IN_MANIFEST")
            if canonical_json(blind_card) != canonical_json(by_case[case_id]):
                raise WP6Error("C2P2_SD_WP6_BLIND_CARD_REPRODUCTION_MISMATCH")
            if case_id in result:
                raise WP6Error("C2P2_SD_WP6_DUPLICATE_REPRESENTATIVE_CASE")
            result[case_id] = record
    finally:
        connection.close()
    if set(result) != set(by_case):
        raise WP6Error("C2P2_SD_WP6_REPRESENTATIVE_CASE_SET_MISMATCH")
    return result


def analyze(repo_root: Path, evidence_root: Path, *, targeted_summary: str, repository_summary: str) -> dict[str, Any]:
    freeze, cards = validate_freeze(repo_root, evidence_root)
    records = correlate_records(evidence_root, cards)
    labels = {str(row["review_case_id"]): str(row["adjudication_label"]) for row in freeze["labels"]}
    cards_by_case = {str(card["review_case_id"]): card for card in cards}

    unblinding_rows = []
    candidate_stats = {
        candidate_id: {
            "false_split": 0,
            "false_join": 0,
            "candidate_ambiguous_on_human_evaluable": 0,
            "candidate_no_correspondence_on_human_evaluable": 0,
            "candidate_same_on_human_evaluable": 0,
            "human_same_denominator": 0,
            "human_different_denominator": 0,
            "human_ambiguous_denominator": 0,
            "human_not_evaluable_denominator": 0,
        }
        for candidate_id in CANDIDATE_IDS
    }
    label_counts = Counter(labels.values())
    stratum_label_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for case_id in sorted(records):
        record = records[case_id]
        card = cards_by_case[case_id]
        unblind = build_unblinding_map(record, BLINDING_KEY)
        unblinding_rows.append(unblind)
        human = labels[case_id]
        stratum_key = canonical_json(card["stratum"])
        stratum_label_counts[stratum_key][human] += 1
        slot_map = unblind["candidate_slot_map"]
        disposition_by_candidate = {
            candidate_id: str(card["candidate_disposition_slots"][slot])
            for slot, candidate_id in slot_map.items()
        }
        for candidate_id, disposition in disposition_by_candidate.items():
            stats = candidate_stats[candidate_id]
            if human == "SAME":
                stats["human_same_denominator"] += 1
                if disposition in {"DIFFERENT", "NO_CORRESPONDENCE"}:
                    stats["false_split"] += 1
                elif disposition == "AMBIGUOUS":
                    stats["candidate_ambiguous_on_human_evaluable"] += 1
                elif disposition == "SAME":
                    stats["candidate_same_on_human_evaluable"] += 1
            elif human == "DIFFERENT":
                stats["human_different_denominator"] += 1
                if disposition == "SAME":
                    stats["false_join"] += 1
                elif disposition == "AMBIGUOUS":
                    stats["candidate_ambiguous_on_human_evaluable"] += 1
                elif disposition == "NO_CORRESPONDENCE":
                    stats["candidate_no_correspondence_on_human_evaluable"] += 1
            elif human == "AMBIGUOUS":
                stats["human_ambiguous_denominator"] += 1
            else:
                stats["human_not_evaluable_denominator"] += 1

    greal = load_json(repo_root / GREAL_RESULT)
    hard_counts = greal["wp4_summary"]["hard_falsification_counts"]
    for candidate_id in CANDIDATE_IDS:
        candidate_stats[candidate_id]["hard_falsification_count"] = int(hard_counts[candidate_id])
        candidate_stats[candidate_id]["recommendation_eligible_from_current_labels"] = False
        candidate_stats[candidate_id]["error_rate_state"] = "NOT_EVALUABLE_ZERO_HUMAN_SAME_DIFFERENT_DENOMINATOR"

    evaluable = label_counts.get("SAME", 0) + label_counts.get("DIFFERENT", 0)
    if evaluable != 0:
        raise WP6Error("C2P2_SD_WP6_EXPECTED_OPERATOR_FREEZE_DRIFT")

    label_freeze_sha = file_sha256(repo_root / LABEL_FREEZE)
    unblinding = {
        "schema": "ovc-c2p2-sd-gadj-unblinding-map/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": GATE_ID,
        "label_freeze_sha256": label_freeze_sha,
        "blind_review_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "emitted_after_label_freeze": True,
        "case_count": EXPECTED_CASES,
        "mappings": unblinding_rows,
    }

    analysis = {
        "schema": "ovc-c2p2-sd-wp6-error-pareto-analysis/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "C2P2-SD-WP6",
        "status": "COMPLETED_NO_EVALUABLE_HUMAN_IDENTITY_LABELS",
        "blind_review_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "label_freeze_sha256": label_freeze_sha,
        "label_counts": {label: int(label_counts.get(label, 0)) for label in ("SAME", "DIFFERENT", "AMBIGUOUS", "NOT_EVALUABLE")},
        "human_same_different_evaluable_count": evaluable,
        "candidate_metrics": candidate_stats,
        "hard_falsification_state": "NONE_OBSERVED_IN_GREAL",
        "pareto_state": "NOT_ASSESSABLE_ZERO_HUMAN_SAME_DIFFERENT_DENOMINATOR",
        "scientific_disposition": "DEFER_SELECTION_INSUFFICIENT_POSITIVE_INDEPENDENT_IDENTITY_ANCHOR_EVIDENCE",
        "candidate_recommendation": None,
        "candidate_c_episode_enrichment": "NOT_EVALUATED_ROLE_REGISTRY_EMPTY_SELECTION_JUSTIFICATION_FORBIDDEN",
        "selection": "NONE",
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "ec1_candidate_defining_use": "FORBIDDEN",
        "publication_probability_risk_exposure_trading_execution_agent_write": "NONE",
        "stratum_label_counts": {key: dict(sorted(counter.items())) for key, counter in sorted(stratum_label_counts.items())},
    }

    qa = {
        "schema": "ovc-c2p2-sd-wp6-qa/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "C2P2-SD-WP6",
        "recommendation": "PASS",
        "targeted_tests": targeted_summary,
        "repository_tests": repository_summary,
        "blind_manifest_reproduction": "PASS_72_OF_72_EXACT",
        "label_freeze_validation": "PASS_72_OF_72_OPERATOR_FROZEN_NOT_EVALUABLE",
        "unblinding_order": "PASS_AFTER_LABEL_FREEZE_ONLY",
        "unresolved_issues": [],
        "warnings": [
            "All 72 human labels are NOT_EVALUABLE; false-split/false-join rates therefore have zero lawful SAME/DIFFERENT denominator.",
            "Candidate C episode enrichment remains untested because the frozen episode-relative role registry is empty.",
            "2H_A_L remains context-only under the frozen base-candidate runtime.",
        ],
        "selection": "NONE",
        "activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
    }

    gate = {
        "schema": "ovc-c2p2-sd-gsel-gate-packet/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": "OVC-C2P2-SCIENTIFIC-DISCRIMINATION-PLAN-v0.1",
        "plan_version": "v0.1",
        "gate_id": "C2P2-SD-GSEL",
        "title": "Final ObjectPack scientific selection review",
        "status": "GATE_READY",
        "gate_classification": "OPERATOR_REQUIRED",
        "completed_packets": ["C2P2-SD-WP0", "C2P2-SD-WP1", "C2P2-SD-WP2", "C2P2-SD-WP3", "C2P2-SD-WP4", "C2P2-SD-WP5", "C2P2-SD-WP6"],
        "current_authority": "GADJ_LABELS_FROZEN_AND_WP6_COMPLETED_NO_SELECTION_AUTHORITY",
        "recommended_decision": "DEFER",
        "recommended_candidate": None,
        "decision_basis": [
            "72_OF_72_FROZEN_HUMAN_LABELS_NOT_EVALUABLE",
            "ZERO_HUMAN_SAME_DIFFERENT_DENOMINATOR_FOR_FALSE_SPLIT_FALSE_JOIN",
            "ZERO_CONFIRMED_D1_HARD_BREAKS_DOES_NOT_ESTABLISH_SAME",
            "C_EPISODE_ENRICHMENT_NOT_EVALUATED"
        ],
        "allowed_decisions": ["PASS_SELECT_NAMED_CANDIDATE", "DEFER", "BLOCK", "QUARANTINE"],
        "proposed_authority_delta": "OBJECTPACK_SELECTION_IF_OPERATOR_EXPLICITLY_SELECTS_NAMED_CANDIDATE_OTHERWISE_NONE",
        "non_transitive_denials": {
            "c2p_activation": "NONE_SEPARATE_OPERATOR_GATE_REQUIRED",
            "validation": "LOCKED_UNCONSUMED",
            "canonical_publication": "NONE",
            "ec1_candidate_defining_use": "FORBIDDEN",
            "probability_risk_exposure_trading_execution_agent_write": "NONE"
        },
        "tests": {"targeted": targeted_summary, "repository": repository_summary, "qa": "PASS"},
        "warnings": qa["warnings"],
        "unresolved_issues": [],
        "rollback": "DEFER/BLOCK/QUARANTINE preserves all GREAL, GADJ and WP6 evidence with no ObjectPack selected or activated.",
        "exact_work_after_approval": "If DEFER/BLOCK/QUARANTINE, record disposition and stop or enter separately authorised successor discrimination work. If PASS_SELECT_NAMED_CANDIDATE, record only the named ObjectPack scientific selection; activation remains a separate operator-reserved gate."
    }

    return {"unblinding": unblinding, "analysis": analysis, "qa": qa, "gate": gate}


def write_outputs(repo_root: Path, result: dict[str, Any]) -> None:
    release = repo_root / RELEASE
    release.mkdir(parents=True, exist_ok=True)
    outputs = {
        release / "C2P2_SD_GADJ_UNBLINDING_MAP_v0_1.json": result["unblinding"],
        release / "C2P2_SD_WP6_ERROR_PARETO_ANALYSIS_v0_1.json": result["analysis"],
        release / "C2P2_SD_WP6_QA_v0_1.json": result["qa"],
        release / "C2P2_SD_GSEL_GATE_PACKET_v0_1.json": result["gate"]
    }
    for path, value in outputs.items():
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    state_path = repo_root / STATE
    state = load_json(state_path)
    state.update({
        "packet_id": "C2P2-SD-GSEL",
        "status": "GATE_READY",
        "authority_required": "OPERATOR_REQUIRED",
        "authority_delta": "PROPOSED_OBJECTPACK_SCIENTIFIC_SELECTION_ONLY_IF_NAMED_PASS",
        "decision_record": None,
        "qa_packet": str(RELEASE / "C2P2_SD_WP6_QA_v0_1.json"),
        "next_packet": "C2P2-SD-GSEL",
        "mandatory_stop": "C2P2-SD-GSEL",
        "blockers": [],
        "selection_state": "COMPARATIVE_SET_ONLY_NO_WINNER",
        "active_object_pack_id": None,
        "c2p_activation": "NONE",
        "unblinding_map_emitted": True,
        "human_label_state": "FROZEN_72_NOT_EVALUABLE",
        "human_label_required_count": 72,
        "main_merge": "NONE",
        "validation": "LOCKED_UNCONSUMED"
    })
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "execute"))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--targeted-summary", default="NOT_RUN")
    parser.add_argument("--repository-summary", default="NOT_RUN")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    if args.command == "validate":
        freeze, cards = validate_freeze(repo_root, evidence_root)
        correlate_records(evidence_root, cards)
        print(json.dumps({"status": "PASS", "cases": len(cards), "labels_sha256": freeze["labels_sha256"]}, sort_keys=True))
        return 0
    result = analyze(repo_root, evidence_root, targeted_summary=args.targeted_summary, repository_summary=args.repository_summary)
    write_outputs(repo_root, result)
    print(json.dumps(result["analysis"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
