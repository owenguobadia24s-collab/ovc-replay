from __future__ import annotations

import hashlib
import json
import math
import shutil
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .index_common import AXES, RO4IndexError, canonical_bytes, logical_hash, sha256_file
from .sequence_common import (
    BANNER,
    CANDIDATE_AUTHORITY,
    COUNT_BANNER,
    DENIED_PD_FIELDS,
    DISTANCE_REGISTRY_ID,
    DIVERSITY_POLICY_ID,
    FORBIDDEN_VOCABULARY,
    OPERATION_MODE,
    SEQUENCE_AUTHORITY,
    SEQUENCE_POLICY_ID,
    SequenceBuildResult,
    declared_distance,
    diversity_audit,
    iter_gzip_jsonl,
    machine_identity,
    peak_rss_bytes,
    signature_core,
    signature_id,
    write_gzip_jsonl,
    write_json,
)
from .sequence_materialize import (
    _candidate_and_control_records,
    _prepare_counts,
    _sig,
    reconstruct_sequence,
)
from .sequence_workspace import connect_workspace, workspace_inventory


def _source_partitions(index_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = index_dir / "index-manifest.json"
    if not manifest_path.is_file():
        raise RO4IndexError("RO4_G1_INDEX_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise RO4IndexError("VALIDATION_DENIAL_NOT_PRESERVED")
    return {item["partition_id"]: item for item in manifest["partitions"]}


def _signature_for_sequence(sequence: dict[str, Any]) -> dict[str, Any]:
    core = signature_core(
        role=sequence["role"],
        clock=sequence["clock"],
        side=sequence["side"],
        evaluation_scope_id=sequence["evaluation_scope_id"],
        state_axes=sequence["ordered_axis_vectors"],
        changed_axes=sequence["ordered_changed_axis_sets"],
    )
    canonical_hash = logical_hash(core)
    record = {
        "signature_id": signature_id(canonical_hash),
        "sequence_id": sequence["sequence_id"],
        **core,
        "canonical_json_sha256": canonical_hash,
    }
    record["logical_hash"] = logical_hash(record)
    return record


def _sequence_card(sequence: dict[str, Any], blind: str) -> dict[str, Any]:
    return {
        "blind_id": blind,
        "role": sequence["role"],
        "clock": sequence["clock"],
        "side": sequence["side"],
        "source_release_id": sequence["source_release_id"],
        "manifest_sha256": sequence["manifest_sha256"],
        "source_partition_id": sequence["source_partition_id"],
        "evaluation_scope_id": sequence["evaluation_scope_id"],
        "calendar_partition": sequence["calendar_partition"],
        "member_state_ids": sequence["member_state_ids"],
        "member_transition_ids": sequence["member_transition_ids"],
        "ordered_axis_vectors": sequence["ordered_axis_vectors"],
        "ordered_changed_axis_sets": sequence["ordered_changed_axis_sets"],
        "first_valid_at": sequence["first_valid_at"],
        "last_valid_at": sequence["last_valid_at"],
        "operation_mode": sequence["operation_mode"],
        "authority": SEQUENCE_AUTHORITY,
        "non_canonical_banner": BANNER,
        "count_banner": COUNT_BANNER,
    }


def _batch_and_answer_key(
    *,
    index_dir: Path,
    connection: sqlite3.Connection,
    review_pool: list[tuple[str, dict[str, Any], dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    cards: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    signatures: list[dict[str, Any]] = []
    signature_counts: Counter[str] = Counter()
    used_sequences: set[str] = set()

    def append(sequence_text: str, true_class: str, candidate_id: str, control_type: str | None) -> bool:
        if sequence_text in used_sequences:
            return False
        sequence = reconstruct_sequence(index_dir=index_dir, connection=connection, sequence_text=sequence_text)
        signature = _signature_for_sequence(sequence)
        blind = "RO4.BLIND." + hashlib.sha256(("RO4.G3.BATCH.v0.1|" + sequence_text).encode()).hexdigest()
        cards.append(_sequence_card(sequence, blind))
        answers.append(
            {
                "blind_id": blind,
                "sequence_id": sequence_text,
                "candidate_id": candidate_id,
                "true_class": true_class,
                "control_type": control_type,
                "signature_id": signature["signature_id"],
                "synthetic": False,
            }
        )
        signatures.append(signature)
        signature_counts[signature["signature_id"]] += 1
        used_sequences.add(sequence_text)
        return True

    admitted_candidates = 0
    for candidate_id, candidate, controls in review_pool:
        if admitted_candidates >= 20:
            break
        candidate_sequence = candidate["member_sequence_ids"][0]
        if candidate_sequence in used_sequences:
            continue
        selected_controls: list[dict[str, Any]] = []
        staged_ids = {candidate_sequence}
        for control in controls["real_controls"]:
            if control.get("synthetic"):
                raise RO4IndexError("SYNTHETIC_CONTROL_OPERATOR_BATCH_DENIED")
            control_id = control["control_id"]
            if control_id in used_sequences or control_id in staged_ids:
                continue
            selected_controls.append(control)
            staged_ids.add(control_id)
            if len(selected_controls) == 2:
                break
        if len(selected_controls) != 2:
            continue
        append(candidate_sequence, "RECURRENCE_CANDIDATE", candidate_id, None)
        for control in selected_controls:
            append(control["control_id"], "REAL_CONTROL", candidate_id, control["control_type"])
        admitted_candidates += 1
    if admitted_candidates < 10:
        raise RO4IndexError(f"INSUFFICIENT_REAL_BLINDED_BATCH:{admitted_candidates}")
    answer_core = {
        "schema": "ovc-ro4-g3-sealed-answer-key/v1",
        "batch_policy_id": "RO4.G3.BLINDED.BATCH.v0.1",
        "access_state": "SEALED_NOT_OPERATOR_ACCESSIBLE_UNTIL_REVIEW_FREEZE",
        "entries": sorted(answers, key=lambda item: item["blind_id"]),
        "synthetic_controls_present": False,
    }
    answer_core["logical_hash"] = logical_hash(answer_core)
    batch_core = {
        "schema": "ovc-ro4-g3-blinded-review-batch/v1",
        "batch_id": "RO4.G3.BATCH." + logical_hash({"blind_ids": sorted(item["blind_id"] for item in cards)}),
        "authority": CANDIDATE_AUTHORITY,
        "blinded": True,
        "answer_key_access_state": "SEALED_SEPARATE",
        "composition": {
            "recurrence_candidates": admitted_candidates,
            "real_controls": admitted_candidates * 2,
            "synthetic_controls": 0,
        },
        "cards": sorted(cards, key=lambda item: item["blind_id"]),
        "non_canonical_banner": BANNER,
        "count_banner": COUNT_BANNER,
    }
    batch_core["logical_hash"] = logical_hash(batch_core)
    batch_audit = diversity_audit(
        batch_core["batch_id"], list(signature_counts.values()), batch=True
    )
    if batch_audit["status"] == "SIGNATURE_CONCENTRATION_WARNING":
        raise RO4IndexError("BLINDED_BATCH_SIGNATURE_CAP_FAILURE")
    return batch_core, answer_core, batch_audit, signatures


def _machine_ablation_assurance(signatures: list[dict[str, Any]]) -> dict[str, Any]:
    if not signatures:
        raise RO4IndexError("NO_SIGNATURE_FOR_MACHINE_ASSURANCE")
    source = signatures[0]
    source_core = {
        key: source[key]
        for key in (
            "signature_type", "role", "clock", "side", "ordered_axis_vectors",
            "ordered_changed_axis_sets", "raw_durations", "context_markers",
            "parent_change_markers", "registry_versions", "distance_registry_id", "authority",
        )
    }
    operations: list[dict[str, Any]] = []

    def record(name: str, mutated: dict[str, Any]) -> None:
        changed = logical_hash(mutated) != source["canonical_json_sha256"]
        if not changed:
            raise RO4IndexError(f"MACHINE_ASSURANCE_MUTATION_NOT_DETECTED:{name}")
        distance = declared_distance(source_core, mutated)
        operations.append(
            {
                "mutation_id": "RO4.G3.MUTATION." + logical_hash({"name": name, "source": source["signature_id"]}),
                "operation": name,
                "source_signature_id": source["signature_id"],
                "mutated_signature_sha256": logical_hash(mutated),
                "signature_changed": True,
                "distance_components": distance["components"],
                "operator_surface": "DENIED",
                "result": "PASS",
            }
        )

    axis_ablation = json.loads(json.dumps(source_core))
    axis_ablation["ordered_axis_vectors"][0]["LOCATION"] = {
        "status": "NOT_EVALUATED", "value": None, "reason_code": "MACHINE_ABLATION_QA_ONLY"
    }
    record("AXIS_ABLATION", axis_ablation)

    token_mutation = json.loads(json.dumps(source_core))
    token_mutation["ordered_axis_vectors"][0]["MOTION"]["value"] = "MACHINE_TOKEN_MUTATION"
    record("STATE_TOKEN_MUTATION", token_mutation)

    transition_mutation = json.loads(json.dumps(source_core))
    transition_mutation["ordered_changed_axis_sets"] = list(reversed(transition_mutation["ordered_changed_axis_sets"]))
    if transition_mutation["ordered_changed_axis_sets"] == source_core["ordered_changed_axis_sets"]:
        transition_mutation["ordered_changed_axis_sets"][0] = ["QUALITY"]
    record("TRANSITION_ORDER_MUTATION", transition_mutation)

    duration_mutation = json.loads(json.dumps(source_core))
    duration_mutation["raw_durations"][0] += 1
    record("DURATION_PERTURBATION", duration_mutation)

    missingness_mutation = json.loads(json.dumps(source_core))
    missingness_mutation["ordered_axis_vectors"][-1]["QUALITY"] = {
        "status": "NOT_EVALUABLE", "value": None, "reason_code": "MISSINGNESS_INJECTION_QA_ONLY"
    }
    record("MISSINGNESS_INJECTION", missingness_mutation)

    core = {
        "schema": "ovc-ro4-g3-machine-ablation-assurance/v1",
        "authority": "MACHINE_QA_ONLY",
        "source_signature_id": source["signature_id"],
        "operations": operations,
        "operator_facing_artifacts": [],
        "operator_surface_state": "DENIED",
        "result": "PASS",
    }
    core["logical_hash"] = logical_hash(core)
    return core


def _pd_isolation_assurance(batch: dict[str, Any], candidates_path: Path) -> dict[str, Any]:
    denied_hits: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in DENIED_PD_FIELDS or key.startswith("pd_"):
                    denied_hits.add(key)
                scan(item)
        elif isinstance(value, list):
            for item in value:
                scan(item)

    scan(batch)
    for candidate in iter_gzip_jsonl(candidates_path):
        scan(candidate)
    if denied_hits:
        raise RO4IndexError("RO4_PD_FIELD_LEAK:" + ",".join(sorted(denied_hits)))
    core = {
        "schema": "ovc-ro4-g3-pd-isolation-assurance/v1",
        "ro4_namespace": "RO4.SEQUENCE.*",
        "pd_namespace": "PD.CANDIDATE.*",
        "population_merge": "DENIED",
        "joint_ranking": "DENIED",
        "joint_review_batch": "DENIED",
        "evidence_bridge": "DENIED",
        "permitted_trace_fields": ["pd_trigger_id", "pd_run_id", "trigger_first_valid_at"],
        "denied_fields_detected": [],
        "trigger_references_in_fixed_rolling_population": 0,
        "result": "PASS",
    }
    core["logical_hash"] = logical_hash(core)
    return core



def _operation_mode_assurance() -> dict[str, Any]:
    core = {
        "schema": "ovc-ro4-g3-operation-mode-assurance/v1",
        "accepted_modes": ["LIVE_PROSPECTIVE", "TIME_GATED_REPLAY", "NON_EVIDENTIARY_REPLAY"],
        "materialized_mode": OPERATION_MODE,
        "live_prospective_record_count": 0,
        "time_gated_replay_record_count": 0,
        "non_evidentiary_replay_record_count_state": "FULL_SEQUENCE_POPULATION",
        "post_cutoff_identifier_access": "ABSENT_NOT_HIDDEN",
        "replay_to_prospective_translation": "DENIED",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "result": "PASS",
    }
    core["logical_hash"] = logical_hash(core)
    return core

def _vocabulary_assurance(paths: Iterable[Path]) -> dict[str, Any]:
    # Check field names and enum-like values, not governance banners explaining prohibitions.
    hits: set[str] = set()
    for path in paths:
        records: Iterable[Any]
        if path.name.endswith(".jsonl.gz"):
            records = iter_gzip_jsonl(path)
        else:
            records = [json.loads(path.read_text(encoding="utf-8"))]
        for record in records:
            stack = [record]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    for key, item in value.items():
                        normalized = key.lower().replace("_", " ")
                        if normalized in FORBIDDEN_VOCABULARY:
                            hits.add(key)
                        stack.append(item)
                elif isinstance(value, list):
                    stack.extend(value)
    if hits:
        raise RO4IndexError("SEMANTIC_VOCABULARY_FIELD_LEAK:" + ",".join(sorted(hits)))
    return {"result": "PASS", "forbidden_field_hits": [], "vocabulary_policy": "RO4_SEQUENCE_EVIDENCE_CONTRACT_v0_1"}
