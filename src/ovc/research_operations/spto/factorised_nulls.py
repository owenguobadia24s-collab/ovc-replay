"""Source-free coupled-null qualification for the factorised grammar protocol."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Callable, Mapping, Sequence

from .factorised_mechanics import DECLARED_REPRESENTATIONS, PROTOCOL_SHA256, content_id


NULL_SPECS = {
    "FG-NC": {
        "transformation": "CARRIER_WITHIN_OPERATION_ISO_WEEK_PERMUTATION",
        "claim": "H1-CARRIER",
        "role": "PRIMARY",
        "strata": ("segment_id", "iso_week", "last_operation", "path_length"),
    },
    "FG-NO": {
        "transformation": "OPERATION_PATH_WITHIN_HI_CARRIER_ISO_WEEK_PERMUTATION",
        "claim": "H2-OPERATION",
        "role": "PRIMARY",
        "strata": ("segment_id", "iso_week", "hi_carrier", "path_length"),
    },
    "FG-NORD": {
        "transformation": "WITHIN_INTERVAL_CARRIER_OPERATION_ORDER_PERMUTATION",
        "claim": "H3-ORDER",
        "role": "PRIMARY",
        "strata": ("event_id",),
    },
    "FG-NCORE": {
        "transformation": "FACTOR_PATH_WITHIN_LAST_OPERATION_ISO_WEEK_PERMUTATION",
        "claim": "H4-CORE",
        "role": "PRIMARY",
        "strata": ("segment_id", "iso_week", "last_operation", "path_length"),
    },
    "FG-NFO": {
        "transformation": "FIRST_ORDER_FACTOR_TOKEN_MARKOV_REFERENCE",
        "claim": "H5-HIGHER_ORDER",
        "role": "PRIMARY",
        "strata": ("segment_id",),
    },
    "FG-NBROAD": {
        "transformation": "WHOLE_FACTOR_PATH_WITHIN_ISO_WEEK_SHUFFLE",
        "claim": "SENSITIVITY_BROAD_LOCAL_COMPOSITION",
        "role": "SENSITIVITY_ONLY",
        "strata": ("segment_id", "iso_week", "path_length"),
    },
}
REPLICAS_PER_NULL = 128


class NullQualificationError(ValueError):
    def __init__(self, reason_code: str, detail: str):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _seed(null_id: str, replica_index: int) -> str:
    return hashlib.sha256(
        f"{PROTOCOL_SHA256}\n{null_id}\n{replica_index}".encode("utf-8")
    ).hexdigest()


def _permutation(items: Sequence[Any], seed: str, identity: Callable[[Any], str]) -> list[Any]:
    return sorted(
        items,
        key=lambda item: hashlib.sha256(f"{seed}\n{identity(item)}".encode("utf-8")).hexdigest(),
    )


def _groups(events: Sequence[dict[str, Any]], fields: Sequence[str]) -> list[list[dict[str, Any]]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        event["path_length"] = len(event["path"])
        groups[tuple(event[field] for field in fields)].append(event)
    return [groups[key] for key in sorted(groups, key=repr)]


def _permute_component(
    events: list[dict[str, Any]], fields: Sequence[str], seed: str, component: str
) -> None:
    for group in _groups(events, fields):
        donors = _permutation(group, seed, lambda event: event["event_id"])
        payloads = [copy.deepcopy(donor[component]) for donor in donors]
        for recipient, payload in zip(sorted(group, key=lambda event: event["event_id"]), payloads):
            recipient[component] = payload


def _markov_world(events: list[dict[str, Any]], seed: str) -> None:
    training = [event for event in events if event["population_role"] == "TRAINING"]
    if not training:
        raise NullQualificationError("FIRST_ORDER_NULL_INADEQUATE", "no training events")
    starts: Counter[str] = Counter()
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    token_payload: dict[str, dict[str, str]] = {}
    for event in training:
        tokens = []
        for relation in event["path"]:
            token = content_id("FirstOrderFactorToken/v1", relation)
            token_payload[token] = copy.deepcopy(relation)
            tokens.append(token)
        if tokens:
            starts[tokens[0]] += 1
        for left, right in zip(tokens, tokens[1:]):
            transitions[left][right] += 1
    if not starts:
        raise NullQualificationError("FIRST_ORDER_NULL_INADEQUATE", "empty training paths")

    def choose(counter: Mapping[str, int], key: str) -> str:
        expanded = [token for token, count in sorted(counter.items()) for _ in range(count)]
        index = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % len(expanded)
        return expanded[index]

    for event in events:
        length = len(event["path"])
        if not length:
            continue
        current = choose(starts, f"{seed}\n{event['event_id']}\n0")
        generated = [copy.deepcopy(token_payload[current])]
        for index in range(1, length):
            options = transitions.get(current) or starts
            current = choose(options, f"{seed}\n{event['event_id']}\n{index}")
            generated.append(copy.deepcopy(token_payload[current]))
        event["path"] = generated
        event["last_operation"] = generated[-1]["operation"]
        event["hi_carrier"] = generated[-1]["carrier_hi"]


def transform_null_world(
    null_id: str, replica_index: int, source_events: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if null_id not in NULL_SPECS or not 0 <= replica_index < REPLICAS_PER_NULL:
        raise NullQualificationError("UNDECLARED_NULL", f"{null_id}:{replica_index}")
    events = _json_value(source_events)
    seed = _seed(null_id, replica_index)
    spec = NULL_SPECS[null_id]
    if null_id == "FG-NC":
        for event in events:
            event["carrier_path"] = [relation["carrier"] for relation in event["path"]]
        _permute_component(events, spec["strata"], seed, "carrier_path")
        for event in events:
            for relation, carrier in zip(event["path"], event.pop("carrier_path")):
                relation["carrier"] = carrier
    elif null_id == "FG-NO":
        for event in events:
            event["operation_path"] = [relation["operation"] for relation in event["path"]]
        _permute_component(events, spec["strata"], seed, "operation_path")
        for event in events:
            for relation, operation in zip(event["path"], event.pop("operation_path")):
                relation["operation"] = operation
            event["last_operation"] = event["path"][-1]["operation"]
    elif null_id == "FG-NORD":
        for event in events:
            event["path"] = _permutation(
                event["path"], f"{seed}\n{event['event_id']}",
                lambda relation: content_id("FactorRelation/v1", relation),
            )
            event["last_operation"] = event["path"][-1]["operation"]
            event["hi_carrier"] = event["path"][-1]["carrier_hi"]
    elif null_id in {"FG-NCORE", "FG-NBROAD"}:
        _permute_component(events, spec["strata"], seed, "path")
        for event in events:
            event["last_operation"] = event["path"][-1]["operation"]
            event["hi_carrier"] = event["path"][-1]["carrier_hi"]
    else:
        _markov_world(events, seed)
    for event in events:
        event.pop("path_length", None)
    events.sort(key=lambda event: event["event_id"])
    body = {"null_id": null_id, "replica_index": replica_index, "seed_hex": seed, "events": events}
    body["source_world_id"] = content_id("FactorisedNullSourceWorld/v1", body)
    return body


def derive_representation_bundle(world: Mapping[str, Any]) -> dict[str, Any]:
    view_ids = []
    for representation_id in DECLARED_REPRESENTATIONS:
        value = {
            "representation_id": representation_id,
            "source_world_id": world["source_world_id"],
            "event_ids": [event["event_id"] for event in world["events"]],
            "path_ids": [content_id(f"NullPath:{representation_id}", event["path"]) for event in world["events"]],
        }
        view_ids.append((representation_id, content_id("NullDerivedRepresentationView/v1", value)))
    body = {
        "source_world_id": world["source_world_id"],
        "representation_set": list(DECLARED_REPRESENTATIONS),
        "view_ids": view_ids,
    }
    body["representation_bundle_id"] = content_id("NullRepresentationBundle/v1", body)
    return _json_value(body)


def assess_null_adequacy(
    null_id: str, source_events: Sequence[Mapping[str, Any]], world: Mapping[str, Any], bundle: Mapping[str, Any]
) -> dict[str, Any]:
    original = {event["event_id"]: event for event in _json_value(source_events)}
    transformed = {event["event_id"]: event for event in world["events"]}
    event_membership = set(original) == set(transformed)
    target_preserved = event_membership and all(original[key]["target"] == transformed[key]["target"] for key in original)
    chronology_preserved = event_membership and all(
        (original[key]["segment_id"], original[key]["iso_week"], original[key]["event_time_utc"])
        == (transformed[key]["segment_id"], transformed[key]["iso_week"], transformed[key]["event_time_utc"])
        for key in original
    )
    path_lengths_preserved = event_membership and all(len(original[key]["path"]) == len(transformed[key]["path"]) for key in original)
    complete_views = bundle["representation_set"] == list(DECLARED_REPRESENTATIONS) and len(bundle["view_ids"]) == len(DECLARED_REPRESENTATIONS)
    shared_source = all(view[1] for view in bundle["view_ids"]) and bundle["source_world_id"] == world["source_world_id"]
    training_only_fit = null_id != "FG-NFO" or any(event["population_role"] == "TRAINING" for event in source_events)
    adequate = all((event_membership, target_preserved, chronology_preserved, path_lengths_preserved, complete_views, shared_source, training_only_fit))
    assessment = {
        "null_id": null_id,
        "event_membership_preserved": event_membership,
        "targets_preserved": target_preserved,
        "chronology_and_break_strata_preserved": chronology_preserved,
        "path_length_schedule_preserved": path_lengths_preserved,
        "complete_declared_representation_set_derived": complete_views,
        "single_shared_source_world": shared_source,
        "training_only_fit": training_only_fit,
        "adequate": adequate,
        "failure_disposition": None if adequate else "AFFECTED_CLAIM_NOT_EVALUABLE_NO_SUBSTITUTION",
    }
    assessment["assessment_id"] = content_id("NullAdequacyAssessment/v1", assessment)
    return assessment


def synthetic_null_events() -> list[dict[str, Any]]:
    events = []
    carriers = ["C1", "C2", "C3", "C4"]
    operations = ["O1", "O2", "O3", "O4"]
    for index in range(8):
        path = []
        for step in range(3):
            carrier = carriers[(index + step) % len(carriers)]
            operation = operations[(index * 2 + step) % len(operations)]
            path.append({"carrier": carrier, "carrier_hi": f"HI-{carrier[-1]}", "operation": operation})
        events.append({
            "event_id": f"SYNTH.NULL.EVENT.{index:02d}",
            "segment_id": "SEG-A" if index < 6 else "SEG-B",
            "iso_week": "2021-W50" if index < 6 else "2021-W51",
            "event_time_utc": f"2021-12-{10 + index:02d}T00:00:00Z",
            "last_operation": path[-1]["operation"],
            "hi_carrier": path[-1]["carrier_hi"],
            "path": path,
            "target": f"TARGET-{index % 3}",
            "population_role": "TRAINING" if index < 4 else "EVALUATION",
        })
    return events


def build_null_qualification_pack() -> dict[str, Any]:
    source = synthetic_null_events()
    replicas = []
    family_assessments = {}
    for null_id in NULL_SPECS:
        adequate_count = 0
        for replica_index in range(REPLICAS_PER_NULL):
            world = transform_null_world(null_id, replica_index, source)
            bundle = derive_representation_bundle(world)
            assessment = assess_null_adequacy(null_id, source, world, bundle)
            adequate_count += int(assessment["adequate"])
            replicas.append({
                "null_id": null_id,
                "replica_index": replica_index,
                "seed_hex": world["seed_hex"],
                "source_world_id": world["source_world_id"],
                "representation_bundle_id": bundle["representation_bundle_id"],
                "adequacy_assessment_id": assessment["assessment_id"],
                "adequate": assessment["adequate"],
            })
        family_assessments[null_id] = {
            **NULL_SPECS[null_id],
            "replica_count": REPLICAS_PER_NULL,
            "adequate_replica_count": adequate_count,
            "adequate": adequate_count == REPLICAS_PER_NULL,
            "inadequate_disposition": "AFFECTED_CLAIM_NOT_EVALUABLE_NO_SUBSTITUTION",
        }
    pack = {
        "schema": "ovc-c2s-sptoi-factorised-null-qualification-pack/v0.1",
        "protocol_sha256": PROTOCOL_SHA256,
        "source_fixture_id": content_id("FactorisedNullSyntheticSource/v1", source),
        "null_specs": NULL_SPECS,
        "family_assessments": family_assessments,
        "replicas": replicas,
        "primary_replica_count": 5 * REPLICAS_PER_NULL,
        "sensitivity_replica_count": REPLICAS_PER_NULL,
        "total_replica_count": len(replicas),
        "all_representations_derived_from_one_world_per_replica": True,
        "independent_representation_draws": False,
        "protected_source_access": "NONE",
        "factorised_evidence_execution": "DENIED",
        "result": "PASS_SOURCE_FREE_NULL_QUALIFICATION",
        "authority_effect": "NONE_NULL_MECHANICS_QUALIFICATION_ONLY",
    }
    pack = _json_value(pack)
    pack["pack_id"] = content_id("FactorisedNullQualificationPack/v1", pack)
    return pack
