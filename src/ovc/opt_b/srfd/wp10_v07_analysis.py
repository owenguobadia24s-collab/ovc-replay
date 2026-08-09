from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping, Sequence

from .sensitivity import assignment_map, build_correspondence, sensitivity_metrics
from .serialization import logical_sha256
from .stability_metrics_v04 import (
    ambiguity_rate,
    chronological_stability,
    family_survival_rate,
    qualifies_adjacent_sensitivity,
    qualifies_cross_method,
    residual_rate,
)
from .wp10_v07_contract import ConfigurationDescriptor, WP10RunnerError, SENSITIVITY_LADDERS
from .wp10_v07_family import frozen_configuration_plan

def _analysis_descriptor(
    preparation: Mapping[str, Any], descriptor: ConfigurationDescriptor
) -> dict[str, Any]:
    return {
        "configuration_id": descriptor.configuration_id,
        "representation_id": str(preparation["representation_id"]),
        "distance_id": "GOWER_MIXED",
        "family_method_id": descriptor.family_method_id,
        "shared_minimum_support": descriptor.minimum_support,
        "parameters": descriptor.parameters,
    }



def build_invariant_core_support_exact(catalogs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Capacity-safe exact equivalent of build_invariant_cores(..., minimum_catalog_support=2)."""
    ordered = sorted((dict(item) for item in catalogs), key=lambda item: str(item.get("family_catalog_id", "")))
    if not ordered:
        return {"cores": [], "catalog_denominator": 0, "authority_state": "FIXTURE_ONLY"}
    assignments = [assignment_map(item) for item in ordered]
    all_members = sorted(set().union(*(set(mapping) for mapping in assignments)))
    parent = {member: member for member in all_members}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a == b:
            return
        if a < b:
            parent[b] = a
        else:
            parent[a] = b

    # A pair has support >=2 iff it shares a non-null family in at least one pair
    # of catalogs. Grouping by the two family IDs avoids O(n^2) pair enumeration.
    for left_index in range(len(assignments)):
        left = assignments[left_index]
        for right_index in range(left_index + 1, len(assignments)):
            right = assignments[right_index]
            groups: dict[tuple[str, str], list[str]] = {}
            for member in all_members:
                lf = left.get(member)
                rf = right.get(member)
                if lf is None or rf is None:
                    continue
                groups.setdefault((lf, rf), []).append(member)
            for members in groups.values():
                if len(members) < 2:
                    continue
                anchor = members[0]
                for member in members[1:]:
                    union(anchor, member)

    components: dict[str, list[str]] = {}
    for member in all_members:
        components.setdefault(find(member), []).append(member)
    cores: list[dict[str, Any]] = []
    from .serialization import stable_id
    for members in sorted((sorted(values) for values in components.values() if len(values) >= 2), key=lambda values: values):
        numerator = 0
        for mapping in assignments:
            family_ids = {mapping.get(member) for member in members}
            if len(family_ids) == 1 and None not in family_ids:
                numerator += 1
        payload = {
            "member_ids": members,
            "support_numerator": numerator,
            "support_denominator": len(ordered),
            "minimum_catalog_support": 2,
        }
        cores.append({**payload, "invariant_core_id": stable_id("SRFD.CORE.", payload)})
    result = {
        "cores": sorted(cores, key=lambda item: item["invariant_core_id"]),
        "catalog_denominator": len(ordered),
        "authority_state": "FIXTURE_ONLY",
    }
    return {**result, "logical_hash": logical_sha256(result)}


def method_disagreement_exact(catalogs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Capacity-safe exact method-disagreement calculation without repeated full-map scans."""
    ordered = sorted(
        (dict(item) for item in catalogs),
        key=lambda item: (str(item.get("method_id", "")), str(item.get("family_catalog_id", ""))),
    )
    assignments = [(str(item.get("method_id", "")), assignment_map(item)) for item in ordered]
    family_members: list[dict[str, frozenset[str]]] = []
    for catalog in ordered:
        family_members.append({
            str(family["family_id"]): frozenset(str(value) for value in family.get("member_ids", ()))
            for family in catalog.get("families", ())
        })
    members = sorted(set().union(*(set(mapping) for _, mapping in assignments))) if assignments else []
    disagreements: list[dict[str, Any]] = []
    for member in members:
        statuses = [(method, mapping.get(member)) for method, mapping in assignments]
        normalized = [family is not None for _, family in statuses]
        if len(set(normalized)) > 1:
            disagreements.append({
                "record_id": member,
                "type": "MEMBER_VS_RESIDUAL",
                "method_assignments": statuses,
            })
            continue
        if all(normalized):
            peer_sets: list[tuple[str, frozenset[str]]] = []
            for index, ((method, mapping), (_, family_id)) in enumerate(zip(assignments, statuses)):
                peers = family_members[index][str(family_id)] - {member}
                peer_sets.append((method, peers))
            if len({peers for _, peers in peer_sets}) > 1:
                disagreements.append({
                    "record_id": member,
                    "type": "FAMILY_MEMBERSHIP_DISAGREEMENT",
                    "method_neighborhoods": [
                        (method, tuple(sorted(peers))) for method, peers in peer_sets
                    ],
                })
    payload = {
        "catalog_ids": [item.get("family_catalog_id") for item in ordered],
        "method_count": len(ordered),
        "record_denominator": len(members),
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "composite_score": None,
        "authority_state": "FIXTURE_ONLY",
    }
    from .serialization import stable_id
    return {**payload, "method_disagreement_id": stable_id("SRFD.DISAGREE.", payload), "logical_hash": logical_sha256(payload)}

def analyse_domain(
    records: Sequence[Mapping[str, Any]],
    preparation: Mapping[str, Any],
    catalogs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    descriptors = frozen_configuration_plan(str(preparation["domain_id"]))
    if set(catalogs) != {item.configuration_id for item in descriptors}:
        raise WP10RunnerError("FROZEN_GRID_INCOMPLETE", "analysis catalog set mismatch")
    descriptor_map = {
        item.configuration_id: _analysis_descriptor(preparation, item) for item in descriptors
    }
    ordered_ids = sorted(catalogs)
    per_configuration: list[dict[str, Any]] = []
    first_valid = {
        str(record["representation_id"]): str(record["first_valid_time"]) for record in records
    }
    for config_id in ordered_ids:
        catalog = catalogs[config_id]
        row = {
            "configuration_id": config_id,
            "residual_rate": residual_rate(catalog),
            "chronological_stability": chronological_stability(catalog, first_valid),
        }
        per_configuration.append(row)

    pair_ledger: list[dict[str, Any]] = []
    correspondence_rows: list[dict[str, Any]] = []
    stability_pair_rows: list[dict[str, Any]] = []
    for left_id, right_id in combinations(ordered_ids, 2):
        left_desc = descriptor_map[left_id]
        right_desc = descriptor_map[right_id]
        sensitivity_ok = qualifies_adjacent_sensitivity(left_desc, right_desc, SENSITIVITY_LADDERS)
        cross_method_ok = qualifies_cross_method(left_desc, right_desc)
        pair_ledger.append(
            {
                "left_configuration_id": left_id,
                "right_configuration_id": right_id,
                "adjacent_sensitivity_qualifies": sensitivity_ok,
                "cross_method_qualifies": cross_method_ok,
                "status": "QUALIFYING" if sensitivity_ok or cross_method_ok else "NONQUALIFYING_FROZEN_PAIR",
            }
        )
        if not (sensitivity_ok or cross_method_ok):
            continue
        metric_id = (
            "CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR"
            if sensitivity_ok
            else "CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR"
        )
        for anchor_id, counterpart_id in ((left_id, right_id), (right_id, left_id)):
            anchor = catalogs[anchor_id]
            counterpart = catalogs[counterpart_id]
            correspondence = build_correspondence(anchor, counterpart)
            correspondence_rows.append(
                {
                    "metric_pair_class": metric_id,
                    "anchor_configuration_id": anchor_id,
                    "counterpart_configuration_id": counterpart_id,
                    "correspondence": correspondence,
                }
            )
            stability_pair_rows.append(
                {
                    "metric_id": metric_id,
                    "anchor_configuration_id": anchor_id,
                    "counterpart_configuration_id": counterpart_id,
                    "survival_or_exact_correspondence": family_survival_rate(
                        anchor, counterpart, metric_id=metric_id
                    ),
                    "ambiguity": ambiguity_rate(anchor, counterpart),
                }
            )

    catalog_values = [catalogs[key] for key in ordered_ids]
    invariant = build_invariant_core_support_exact(catalog_values)
    payload = {
        "schema": "ovc-srfdi-wp10-v07-domain-analysis/v1",
        "domain_id": str(preparation["domain_id"]),
        "configuration_count": len(ordered_ids),
        "sensitivity_metrics": sensitivity_metrics(catalog_values),
        "per_configuration_stability": per_configuration,
        "pair_qualification_ledger": pair_ledger,
        "ordered_pair_stability": stability_pair_rows,
        "family_correspondence_split_merge": correspondence_rows,
        "invariant_core_support": invariant,
        "method_disagreement": method_disagreement_exact(catalog_values),
        "scientific_disposition": "NOT_PERFORMED_WP10_EVIDENCE_ONLY_PENDING_G10",
        "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}
