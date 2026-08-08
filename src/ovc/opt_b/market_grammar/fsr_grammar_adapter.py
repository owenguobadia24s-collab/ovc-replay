"""FSR adapter for the existing inactive typed market-grammar compiler/parser.

Important namespace rule: the historical implementation emits parse IDs prefixed
``C2P.PARSE``. Under the forward v0.2 architecture C2P means persistent structural
objects, which are not implemented at the FSR baseline. This module therefore reports
those IDs as *legacy market-grammar parser IDs* and never claims forward-C2P authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from ..srfd.fsr_adapter import _representation_sets
from .typed_grammar import compile_grammar, parse_grammar

PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
AUTHORITY = "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT"


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _grammar_release(*, family_id: str, transition: Mapping[str, Any] | None) -> dict[str, Any]:
    context_node = {
        "operator": "CONTEXT_AVAILABILITY",
        "input_type": "CONTEXT",
        "output_type": "PREDICATE",
        "domain": "CONTEXT",
        "required_fields": [],
        "children": [],
        "parameters": {"required_state": "AVAILABLE"},
    }
    layers: dict[str, Any] = {
        "context": context_node,
        "location": None,
        "condition": None,
        "episode_phase": {
            "operator": "RUN_LENGTH",
            "input_type": "PREDICATE",
            "output_type": "PREDICATE",
            "domain": "SEQUENCE",
            "required_fields": [],
            "children": [context_node],
            "parameters": {"min": 1, "max": 8},
        },
        "event": None,
        "response": None,
        "transition": None,
        "possible_resolution": None,
    }
    if transition is not None:
        layers["transition"] = {
            "operator": "RELATION_TRANSITION",
            "input_type": "RELATION_TRANSITION",
            "output_type": "PREDICATE",
            "domain": "INTERACTION",
            "required_fields": ["transition_evidence"],
            "children": [],
            "parameters": {
                "from": str(transition["previous_topology"]),
                "to": str(transition["current_topology"]),
                "object_binding": str(transition["object_id"]),
            },
        }
    release_id = "FSR.MARKET_GRAMMAR.SHADOW." + _sha({"family_id": family_id, "transition": transition})[:24]
    payload = {
        "grammar_release_id": release_id,
        "layers": layers,
        "invalidating_conditions": ["RESET_BOUNDARY"],
        "canonical": False,
        "published": False,
        "authority_state": "SHADOW_EXPERIMENT",
    }
    return {**payload, "release_sha256": _sha(payload)}


def run_fsr_market_grammar(
    c2_manifest: Mapping[str, Any],
    c2e_manifest: Mapping[str, Any],
    srfd_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    representations, _metadata = _representation_sets(c2_manifest, c2e_manifest)
    r4_by_id = {str(item["representation_id"]): item for item in representations["R4"]}
    snapshot_by_id = {str(item["snapshot_id"]): item for item in c2_manifest["snapshots"]}

    catalogs = [
        item
        for item in srfd_manifest["family_benchmark"]["catalogs"]
        if item.get("families")
    ]
    catalogs.sort(key=lambda item: (str(item["method_id"]), str(item["configuration_id"]), str(item["family_catalog_id"])))
    if not catalogs:
        body = {
            "schema": "ovc-fsr-market-grammar-shadow/v1",
            "programme_id": PROGRAMME_ID,
            "status": "NOT_REACHED_NO_FAMILY_EVIDENCE",
            "reason": "NO_STABLE_FAMILY_IS_A_LAWFUL_TERMINAL_OUTCOME",
            "grammar_count": 0,
            "parse_results": [],
            "hidden_construction_consumed": False,
            "authority": {
                "mode": AUTHORITY,
                "forward_c3_authority": "NONE",
                "forward_c2p_authority": "NONE",
                "canonical_grammar": "NONE",
                "publication": "NONE",
                "validation_consumption": "DENIED",
            },
        }
        body["logical_sha256"] = _sha(body)
        return body

    seed_catalog = catalogs[0]
    families = sorted(seed_catalog["families"], key=lambda item: str(item["family_id"]))
    releases: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for family in families[: min(3, len(families))]:
        member_rep_id = sorted(map(str, family["member_ids"]))[0]
        representation = r4_by_id.get(member_rep_id)
        if representation is None:
            continue
        source_ids = list(representation.get("source_record_ids", []))
        if len(source_ids) != 1 or source_ids[0] not in snapshot_by_id:
            continue
        snapshot = snapshot_by_id[source_ids[0]]
        fixed_context = snapshot.get("parent_context", {}).get("fixed_parent_observation_link", {})
        context_status = "AVAILABLE" if fixed_context.get("computability") == "COMPUTABLE" else "UNAVAILABLE"
        transition = None
        deltas = list(snapshot.get("raw", {}).get("relation_deltas", []))
        changed = [item for item in deltas if item.get("previous_topology") != item.get("current_topology")]
        if changed:
            transition = sorted(changed, key=lambda item: str(item["relation_delta_id"]))[0]
        release_mapping = _grammar_release(family_id=str(family["family_id"]), transition=transition)
        grammar = compile_grammar(release_mapping)
        evidence_transition = []
        fields: dict[str, Any] = {}
        if transition is not None:
            fields["transition_evidence"] = True
            evidence_transition = [{
                "from": transition["previous_topology"],
                "to": transition["current_topology"],
                "object_binding": transition["object_id"],
            }]
        parse = parse_grammar(
            grammar,
            {
                "fields": fields,
                "context_status": context_status,
                "transitions": evidence_transition,
                "observations": [{"context_visible": True}],
                "nearest_family_id": family["family_id"],
                "nearest_variant_id": None,
                "family_distance": None,
                "variant_distance": None,
                "current_phases": ["STRUCTURAL_EVIDENCE_PRESENT"],
                "completed_phases": [],
                "lawful_next_phases": [],
                "missing_evidence": [],
                "conflicting_evidence": [],
                "invalidation_reasons": [],
                "upstream_lineage": [
                    str(c2_manifest["logical_sha256"]),
                    str(c2e_manifest["logical_sha256"]),
                    str(srfd_manifest["logical_sha256"]),
                    str(seed_catalog["family_catalog_id"]),
                    str(representation["logical_hash"]),
                    str(snapshot["snapshot_id"]),
                ],
            },
        ).to_dict()
        results.append(
            {
                **parse,
                "legacy_parser_id": parse["parse_id"],
                "forward_c2p_interpretation": "PROHIBITED_NAMESPACE_REUSE",
                "source_snapshot_id": snapshot["snapshot_id"],
                "source_representation_id": representation["representation_id"],
                "source_family_id": family["family_id"],
                "transition_clause_present": transition is not None,
                "first_valid_time": snapshot["as_of_time"],
            }
        )
        releases.append(grammar.to_dict())

    body = {
        "schema": "ovc-fsr-market-grammar-shadow/v1",
        "programme_id": PROGRAMME_ID,
        "status": "EXECUTED_SHADOW" if results else "NOT_REACHED_NO_LAWFUL_SEED",
        "source_c2_sha256": c2_manifest["logical_sha256"],
        "source_c2e_sha256": c2e_manifest["logical_sha256"],
        "source_srfd_sha256": srfd_manifest["logical_sha256"],
        "source_family_catalog_id": seed_catalog["family_catalog_id"],
        "grammar_count": len(releases),
        "grammar_releases": releases,
        "parse_results": results,
        "parse_status_counts": {
            status: sum(1 for item in results if item["status"] == status)
            for status in sorted({item["status"] for item in results})
        },
        "hidden_construction_consumed": False,
        "authority": {
            "mode": AUTHORITY,
            "forward_c3_authority": "NONE",
            "forward_c2p_authority": "NONE",
            "legacy_parser_namespace_only": True,
            "canonical_grammar": "NONE",
            "semantic_promotion": "NONE",
            "publication": "NONE",
            "validation_consumption": "DENIED",
            "probability_risk_exposure_execution": "NONE",
        },
    }
    body["logical_sha256"] = _sha(body)
    return body
