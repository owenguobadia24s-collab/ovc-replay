from __future__ import annotations

"""Deterministic C2P2-RS0 Candidate–Tracklet–ObjectAssertion runtime.

This module is a research-sidecar runtime only.  It materialises the three
frozen empirical ObjectPack candidates without selecting or activating any of
them, and it never launches or reads the real-source population itself.
"""

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence

from .rs0_empirical_semantics import evaluate_pair, normalize_candidate_source_row


RUNTIME_SCHEMA = "ovc-c2p2-rs0-empirical-runtime-result/v1"
RUNTIME_BINDING_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1"
CONFIRMATION_COUNT = 3


class RS0EmpiricalRuntimeError(ValueError):
    pass


def _hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _scope_key(hard_scope: Mapping[str, Any]) -> str:
    return _hash({"schema": "ovc-c2p2-rs0-hard-scope-key/v1", "hard_scope": hard_scope})


def _candidate_record(candidate_spec: Mapping[str, Any], material: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "ovc-c2p2-rs0-empirical-candidate/v1",
        "object_pack_candidate_id": candidate_spec["candidate_id"],
        "semantic_candidate_id": candidate_spec["semantic_candidate_id"],
        "source_record_id": material["source_record_id"],
        "source_material_hash": material["candidate_material_hash"],
        "structural_role_id": material["structural_role_id"],
        "geometry_kind_id": material["geometry_kind_id"],
        "hard_scope": material["hard_scope"],
        "first_valid_time": material["first_valid_time"],
        "evaluation_cutoff": material["evaluation_cutoff"],
    }
    return {**payload, "candidate_id": _hash(payload)}


def _open_tracklet(candidate: Mapping[str, Any], material: Mapping[str, Any]) -> dict[str, Any]:
    identity = {
        "schema": "ovc-c2p2-rs0-empirical-tracklet-identity/v1",
        "object_pack_candidate_id": candidate["object_pack_candidate_id"],
        "opening_candidate_id": candidate["candidate_id"],
        "hard_scope": candidate["hard_scope"],
    }
    return {
        "schema": "ovc-c2p2-rs0-empirical-tracklet/v1",
        "tracklet_id": _hash(identity),
        "object_pack_candidate_id": candidate["object_pack_candidate_id"],
        "structural_role_id": candidate["structural_role_id"],
        "geometry_kind_id": candidate["geometry_kind_id"],
        "hard_scope": deepcopy(candidate["hard_scope"]),
        "opening_candidate_id": candidate["candidate_id"],
        "member_candidate_ids": [candidate["candidate_id"]],
        "member_source_material_hashes": [candidate["source_material_hash"]],
        "latest_material": deepcopy(dict(material)),
        "state": "OPEN",
        "first_valid_time": candidate["first_valid_time"],
        "evaluation_cutoff": candidate["evaluation_cutoff"],
        "reason_codes": [],
    }


def _append_tracklet(
    tracklet: Mapping[str, Any],
    candidate: Mapping[str, Any],
    material: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(dict(tracklet))
    if result["state"] != "OPEN":
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_TRACKLET_NOT_OPEN")
    if candidate["candidate_id"] in result["member_candidate_ids"]:
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_DUPLICATE_CANDIDATE")
    result["member_candidate_ids"].append(candidate["candidate_id"])
    result["member_source_material_hashes"].append(candidate["source_material_hash"])
    result["latest_material"] = deepcopy(dict(material))
    result["evaluation_cutoff"] = candidate["evaluation_cutoff"]
    if len(result["member_candidate_ids"]) >= CONFIRMATION_COUNT:
        result["state"] = "CONFIRMED"
    return result


def _create_assertion(tracklet: Mapping[str, Any]) -> dict[str, Any]:
    identity = {
        "schema": "ovc-c2p2-rs0-empirical-assertion-identity/v1",
        "object_pack_candidate_id": tracklet["object_pack_candidate_id"],
        "tracklet_id": tracklet["tracklet_id"],
        "hard_scope": tracklet["hard_scope"],
        "immutable_genesis_candidate_ids": tracklet["member_candidate_ids"],
        "first_valid_identity_time": tracklet["first_valid_time"],
    }
    return {
        "schema": "ovc-c2p2-rs0-empirical-object-assertion/v1",
        "object_assertion_id": _hash(identity),
        "object_pack_candidate_id": tracklet["object_pack_candidate_id"],
        "genesis_tracklet_id": tracklet["tracklet_id"],
        "structural_role_id": tracklet["structural_role_id"],
        "geometry_kind_id": tracklet["geometry_kind_id"],
        "hard_scope": deepcopy(tracklet["hard_scope"]),
        "immutable_genesis_candidate_ids": list(tracklet["member_candidate_ids"]),
        "latest_candidate_id": tracklet["member_candidate_ids"][-1],
        "latest_material": deepcopy(tracklet["latest_material"]),
        "observation_count": len(tracklet["member_candidate_ids"]),
        "first_valid_identity_time": tracklet["first_valid_time"],
        "evaluation_cutoff": tracklet["evaluation_cutoff"],
        "lifecycle_state": "ACTIVE_RESEARCH_SIDECAR",
        "activation_state": "NONE",
    }


def _update_assertion(
    assertion: Mapping[str, Any],
    candidate: Mapping[str, Any],
    material: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(dict(assertion))
    result["latest_candidate_id"] = candidate["candidate_id"]
    result["latest_material"] = deepcopy(dict(material))
    result["observation_count"] += 1
    result["evaluation_cutoff"] = candidate["evaluation_cutoff"]
    return result


def _evidence_vector(
    candidate: Mapping[str, Any],
    subject_kind: str,
    subject_id: str,
    pair: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "ovc-c2p2-rs0-empirical-evidence-vector/v1",
        "object_pack_candidate_id": candidate["object_pack_candidate_id"],
        "candidate_id": candidate["candidate_id"],
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "predicate_results": pair["predicate_results"],
        "geometry_residuals": pair["geometry_residuals"],
        "numeric_residual_policy": pair["numeric_residual_policy"],
        "c2e_dependency_disposition": pair["c2e_dependency_disposition"],
        "same_object_pair_supported": pair["same_object_pair_supported"],
    }
    return {**payload, "evidence_vector_id": _hash(payload)}


def _decision(
    candidate: Mapping[str, Any],
    terminal_decision: str,
    *,
    eligible_assertion_ids: Sequence[str] = (),
    eligible_tracklet_ids: Sequence[str] = (),
    evidence_vector_ids: Sequence[str] = (),
    resulting_subject_id: str | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": "ovc-c2p2-rs0-empirical-match-decision/v1",
        "object_pack_candidate_id": candidate["object_pack_candidate_id"],
        "candidate_id": candidate["candidate_id"],
        "eligible_assertion_ids": sorted(eligible_assertion_ids),
        "eligible_tracklet_ids": sorted(eligible_tracklet_ids),
        "evidence_vector_ids": sorted(evidence_vector_ids),
        "terminal_decision": terminal_decision,
        "resulting_subject_id": resulting_subject_id,
        "first_valid_time": candidate["first_valid_time"],
        "evaluation_cutoff": candidate["evaluation_cutoff"],
    }
    return {**payload, "decision_id": _hash(payload)}


def _empty_result(candidate_spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": RUNTIME_SCHEMA,
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "object_pack_candidate_id": candidate_spec["candidate_id"],
        "semantic_candidate_id": candidate_spec["semantic_candidate_id"],
        "selection_state": "UNSELECTED_RESEARCH_CANDIDATE",
        "activation_state": "NONE",
        "real_source_launch": "NOT_AUTHORISED_BY_RUNTIME",
        "processed_source_record_ids": [],
        "last_stream_order_key": None,
        "candidates": [],
        "tracklets": [],
        "object_assertions": [],
        "match_decisions": [],
        "evidence_vectors": [],
        "indexes": {"assertion_ids_by_scope": {}, "open_tracklet_ids_by_scope": {}},
        "checkpoint_sha256": None,
    }


def _validate_initial_state(state: Mapping[str, Any], candidate_spec: Mapping[str, Any]) -> None:
    if state.get("schema") != RUNTIME_SCHEMA:
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_STATE_SCHEMA_INVALID")
    if state.get("runtime_binding_id") != RUNTIME_BINDING_ID:
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_BINDING_MISMATCH")
    if state.get("object_pack_candidate_id") != candidate_spec.get("candidate_id"):
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_OBJECTPACK_CANDIDATE_MISMATCH")
    checkpoint = state.get("checkpoint_sha256")
    payload = {key: value for key, value in state.items() if key != "checkpoint_sha256"}
    if checkpoint != _hash(payload):
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_CHECKPOINT_HASH_MISMATCH")


def _rebuild_indexes(result: dict[str, Any]) -> None:
    assertion_index: dict[str, list[str]] = {}
    for assertion in result["object_assertions"]:
        key = _scope_key(assertion["hard_scope"])
        assertion_index.setdefault(key, []).append(assertion["object_assertion_id"])
    tracklet_index: dict[str, list[str]] = {}
    for tracklet in result["tracklets"]:
        if tracklet["state"] == "OPEN":
            key = _scope_key(tracklet["hard_scope"])
            tracklet_index.setdefault(key, []).append(tracklet["tracklet_id"])
    result["indexes"] = {
        "assertion_ids_by_scope": {key: sorted(value) for key, value in sorted(assertion_index.items())},
        "open_tracklet_ids_by_scope": {key: sorted(value) for key, value in sorted(tracklet_index.items())},
    }


def run_empirical_runtime(
    rows: Iterable[Mapping[str, Any]],
    candidate_spec: Mapping[str, Any],
    dependency_registry: Mapping[str, Any],
    *,
    initial_state: Mapping[str, Any] | None = None,
    explicit_discontinuity_source_ids: Iterable[str] = (),
    prior_terminal_break_source_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Materialise one candidate ObjectPack over rows in canonical stream order.

    The function is restartable through an exact checkpointed ``initial_state``.
    It does not select a pack, mutate source data, activate C2P, or consume GRUN.
    """
    required = {"candidate_id", "semantic_candidate_id", "activation_eligible"}
    if not required.issubset(candidate_spec):
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_CANDIDATE_SPEC_INCOMPLETE")
    if candidate_spec.get("activation_eligible") is not False:
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_ACTIVATION_FORBIDDEN")
    semantic_id = str(candidate_spec["semantic_candidate_id"])
    if not semantic_id.endswith("-v2"):
        raise RS0EmpiricalRuntimeError("RS0_RUNTIME_SEMANTIC_PROFILE_INVALID")

    if initial_state is None:
        result = _empty_result(candidate_spec)
    else:
        _validate_initial_state(initial_state, candidate_spec)
        result = deepcopy(dict(initial_state))
        result["checkpoint_sha256"] = None

    discontinuities = set(explicit_discontinuity_source_ids)
    terminal_breaks = set(prior_terminal_break_source_ids)
    normalized = [normalize_candidate_source_row(row) for row in rows]
    normalized.sort(key=lambda row: (row["first_valid_time"], row["source_record_id"]))
    seen = set(result["processed_source_record_ids"])
    last_key = tuple(result["last_stream_order_key"]) if result["last_stream_order_key"] else None

    tracklet_pos = {row["tracklet_id"]: index for index, row in enumerate(result["tracklets"])}
    assertion_pos = {
        row["object_assertion_id"]: index for index, row in enumerate(result["object_assertions"])
    }
    _rebuild_indexes(result)

    for material in normalized:
        source_id = material["source_record_id"]
        order_key = (material["first_valid_time"], source_id)
        if source_id in seen:
            raise RS0EmpiricalRuntimeError(f"RS0_RUNTIME_DUPLICATE_SOURCE_RECORD:{source_id}")
        if last_key is not None and order_key <= last_key:
            raise RS0EmpiricalRuntimeError("RS0_RUNTIME_NONMONOTONIC_RESTART_STREAM")
        seen.add(source_id)
        candidate = _candidate_record(candidate_spec, material)
        result["candidates"].append(candidate)
        scope = _scope_key(candidate["hard_scope"])
        is_discontinuity = source_id in discontinuities
        is_terminal_break = source_id in terminal_breaks

        assertion_ids = result["indexes"]["assertion_ids_by_scope"].get(scope, [])
        assertion_vectors: list[dict[str, Any]] = []
        eligible_assertions: list[str] = []
        for assertion_id in assertion_ids:
            assertion = result["object_assertions"][assertion_pos[assertion_id]]
            pair = evaluate_pair(
                semantic_id,
                assertion["latest_material"],
                material,
                dependency_registry,
                prior_terminal_break=is_terminal_break,
                explicit_discontinuity=is_discontinuity,
            )
            vector = _evidence_vector(candidate, "OBJECT_ASSERTION", assertion_id, pair)
            assertion_vectors.append(vector)
            if pair["same_object_pair_supported"]:
                eligible_assertions.append(assertion_id)
        result["evidence_vectors"].extend(assertion_vectors)

        if len(eligible_assertions) > 1:
            result["match_decisions"].append(_decision(
                candidate,
                "AMBIGUOUS",
                eligible_assertion_ids=eligible_assertions,
                evidence_vector_ids=[row["evidence_vector_id"] for row in assertion_vectors],
            ))
        elif len(eligible_assertions) == 1:
            assertion_id = eligible_assertions[0]
            position = assertion_pos[assertion_id]
            result["object_assertions"][position] = _update_assertion(
                result["object_assertions"][position], candidate, material
            )
            result["match_decisions"].append(_decision(
                candidate,
                "UPDATE",
                eligible_assertion_ids=[assertion_id],
                evidence_vector_ids=[row["evidence_vector_id"] for row in assertion_vectors],
                resulting_subject_id=assertion_id,
            ))
        else:
            open_ids = result["indexes"]["open_tracklet_ids_by_scope"].get(scope, [])
            tracklet_vectors: list[dict[str, Any]] = []
            eligible_tracklets: list[str] = []
            for tracklet_id in open_ids:
                tracklet = result["tracklets"][tracklet_pos[tracklet_id]]
                pair = evaluate_pair(
                    semantic_id,
                    tracklet["latest_material"],
                    material,
                    dependency_registry,
                    prior_terminal_break=is_terminal_break,
                    explicit_discontinuity=is_discontinuity,
                )
                vector = _evidence_vector(candidate, "TRACKLET", tracklet_id, pair)
                tracklet_vectors.append(vector)
                if pair["same_object_pair_supported"]:
                    eligible_tracklets.append(tracklet_id)
            result["evidence_vectors"].extend(tracklet_vectors)

            if is_discontinuity or is_terminal_break:
                reason = "RS0_EXPLICIT_SOURCE_DISCONTINUITY" if is_discontinuity else "RS0_PRIOR_TERMINAL_BREAK"
                for tracklet_id in open_ids:
                    position = tracklet_pos[tracklet_id]
                    result["tracklets"][position]["state"] = "CENSORED"
                    result["tracklets"][position]["reason_codes"] = [reason]
                eligible_tracklets = []

            if len(eligible_tracklets) > 1:
                for tracklet_id in eligible_tracklets:
                    position = tracklet_pos[tracklet_id]
                    result["tracklets"][position]["state"] = "AMBIGUOUS"
                    result["tracklets"][position]["reason_codes"] = ["RS0_EQUAL_LAWFUL_TRACKLET_COMPETITOR"]
                result["match_decisions"].append(_decision(
                    candidate,
                    "AMBIGUOUS",
                    eligible_tracklet_ids=eligible_tracklets,
                    evidence_vector_ids=[row["evidence_vector_id"] for row in assertion_vectors + tracklet_vectors],
                ))
            elif len(eligible_tracklets) == 1:
                tracklet_id = eligible_tracklets[0]
                position = tracklet_pos[tracklet_id]
                updated = _append_tracklet(result["tracklets"][position], candidate, material)
                result["tracklets"][position] = updated
                if updated["state"] == "CONFIRMED":
                    assertion = _create_assertion(updated)
                    result["object_assertions"].append(assertion)
                    assertion_pos[assertion["object_assertion_id"]] = len(result["object_assertions"]) - 1
                    terminal = "GENESIS"
                    subject_id = assertion["object_assertion_id"]
                else:
                    terminal = "TRACKLET_UPDATE"
                    subject_id = tracklet_id
                result["match_decisions"].append(_decision(
                    candidate,
                    terminal,
                    eligible_tracklet_ids=[tracklet_id],
                    evidence_vector_ids=[row["evidence_vector_id"] for row in assertion_vectors + tracklet_vectors],
                    resulting_subject_id=subject_id,
                ))
            else:
                tracklet = _open_tracklet(candidate, material)
                result["tracklets"].append(tracklet)
                tracklet_pos[tracklet["tracklet_id"]] = len(result["tracklets"]) - 1
                result["match_decisions"].append(_decision(
                    candidate,
                    "NEW_TRACKLET",
                    evidence_vector_ids=[row["evidence_vector_id"] for row in assertion_vectors + tracklet_vectors],
                    resulting_subject_id=tracklet["tracklet_id"],
                ))

        result["processed_source_record_ids"].append(source_id)
        result["last_stream_order_key"] = list(order_key)
        last_key = order_key
        _rebuild_indexes(result)

    result["checkpoint_sha256"] = _hash({
        key: value for key, value in result.items() if key != "checkpoint_sha256"
    })
    return result


def run_comparative_set(
    rows: Iterable[Mapping[str, Any]],
    candidate_specs: Sequence[Mapping[str, Any]],
    dependency_registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Run A/B/C independently without ranking, selecting, or promoting them."""
    frozen_rows = [deepcopy(dict(row)) for row in rows]
    results = [
        run_empirical_runtime(frozen_rows, spec, dependency_registry)
        for spec in sorted(candidate_specs, key=lambda item: item["candidate_id"])
    ]
    payload = {
        "schema": "ovc-c2p2-rs0-empirical-comparative-set/v1",
        "runtime_binding_id": RUNTIME_BINDING_ID,
        "selection_state": "COMPARATIVE_SET_ONLY_NO_WINNER",
        "active_object_pack_id": None,
        "real_source_launch": "NOT_AUTHORISED_BY_RUNTIME",
        "candidate_results": results,
    }
    return {**payload, "comparative_set_sha256": _hash(payload)}
