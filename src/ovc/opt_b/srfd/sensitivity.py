from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from itertools import combinations
from typing import Any, Callable, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id


class SensitivityError(ValueError):
    pass


def _families(catalog: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    output: dict[str, frozenset[str]] = {}
    for family in catalog.get("families", []):
        output[str(family["family_id"])] = frozenset(str(value) for value in family.get("member_ids", []))
    return output


def assignment_map(catalog: Mapping[str, Any]) -> dict[str, str | None]:
    output: dict[str, str | None] = {}
    for family_id, members in _families(catalog).items():
        for member in members:
            output[member] = family_id
    for member in catalog.get("residual_ids", []):
        output.setdefault(str(member), None)
    for member in catalog.get("noise_ids", []):
        output.setdefault(str(member), None)
    return output


def build_correspondence(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    left_families = _families(left); right_families = _families(right)
    edges: list[dict[str, Any]] = []
    for left_id, left_members in sorted(left_families.items()):
        for right_id, right_members in sorted(right_families.items()):
            intersection = left_members & right_members
            if not intersection:
                continue
            union = left_members | right_members
            jaccard = Decimal(len(intersection)) / Decimal(len(union))
            left_containment = Decimal(len(intersection)) / Decimal(len(left_members))
            right_containment = Decimal(len(intersection)) / Decimal(len(right_members))
            payload = {
                "left_family_id": left_id,
                "right_family_id": right_id,
                "shared_member_ids": sorted(intersection),
                "shared_count": len(intersection),
                "jaccard": format(jaccard, "f"),
                "left_containment": format(left_containment, "f"),
                "right_containment": format(right_containment, "f"),
            }
            edges.append({**payload, "correspondence_edge_id": stable_id("SRFD.CORR.", payload)})
    by_left: dict[str, list[str]] = defaultdict(list)
    by_right: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        by_left[edge["left_family_id"]].append(edge["right_family_id"])
        by_right[edge["right_family_id"]].append(edge["left_family_id"])
    split_events = [{"left_family_id": key, "right_family_ids": sorted(values)} for key, values in sorted(by_left.items()) if len(values) > 1]
    merge_events = [{"left_family_ids": sorted(values), "right_family_id": key} for key, values in sorted(by_right.items()) if len(values) > 1]
    payload = {
        "left_catalog_id": str(left.get("family_catalog_id", "")),
        "right_catalog_id": str(right.get("family_catalog_id", "")),
        "edges": sorted(edges, key=lambda item: (item["left_family_id"], item["right_family_id"])),
        "split_events": split_events,
        "merge_events": merge_events,
        "left_family_denominator": len(left_families),
        "right_family_denominator": len(right_families),
        "authority_state": "FIXTURE_ONLY",
    }
    return {**payload, "correspondence_id": stable_id("SRFD.CORRESPONDENCE.", payload), "logical_hash": logical_sha256(payload)}


def sensitivity_metrics(catalogs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted((dict(item) for item in catalogs), key=lambda item: str(item.get("configuration_id", "")))
    outputs: list[dict[str, Any]] = []
    for catalog in ordered:
        assignments = assignment_map(catalog)
        denominator = len(assignments)
        residual = sum(1 for value in assignments.values() if value is None)
        outputs.append({
            "configuration_id": catalog.get("configuration_id"),
            "family_count": len(catalog.get("families", [])),
            "assignment_denominator": denominator,
            "residual_count": residual,
            "residual_rate": format(Decimal(residual) / Decimal(denominator), "f") if denominator else None,
            "evidence_status": catalog.get("evidence_status"),
            "composite_score": None,
        })
    return outputs


def build_invariant_cores(catalogs: Sequence[Mapping[str, Any]], *, minimum_catalog_support: int = 2) -> dict[str, Any]:
    if minimum_catalog_support < 1:
        raise SensitivityError("minimum_catalog_support must be positive")
    ordered = sorted((dict(item) for item in catalogs), key=lambda item: str(item.get("family_catalog_id", "")))
    if not ordered:
        return {"cores": [], "catalog_denominator": 0, "authority_state": "FIXTURE_ONLY"}
    assignments = [assignment_map(item) for item in ordered]
    all_members = sorted(set().union(*(set(mapping) for mapping in assignments)))
    pair_support: dict[tuple[str, str], int] = {}
    for left, right in combinations(all_members, 2):
        support = 0
        for mapping in assignments:
            lf = mapping.get(left); rf = mapping.get(right)
            if lf is not None and lf == rf:
                support += 1
        pair_support[(left, right)] = support
    adjacency: dict[str, set[str]] = {member: set() for member in all_members}
    for (left, right), support in pair_support.items():
        if support >= minimum_catalog_support:
            adjacency[left].add(right); adjacency[right].add(left)
    visited: set[str] = set(); cores: list[dict[str, Any]] = []
    for member in all_members:
        if member in visited:
            continue
        stack = [member]; component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current); component.add(current); stack.extend(sorted(adjacency[current] - visited))
        if len(component) < 2:
            continue
        members = sorted(component)
        numerator = 0
        for mapping in assignments:
            family_ids = {mapping.get(item) for item in members}
            if len(family_ids) == 1 and None not in family_ids:
                numerator += 1
        payload = {
            "member_ids": members,
            "support_numerator": numerator,
            "support_denominator": len(ordered),
            "minimum_catalog_support": minimum_catalog_support,
        }
        cores.append({**payload, "invariant_core_id": stable_id("SRFD.CORE.", payload)})
    payload = {"cores": sorted(cores, key=lambda item:item["invariant_core_id"]), "catalog_denominator": len(ordered), "authority_state":"FIXTURE_ONLY"}
    return {**payload, "logical_hash": logical_sha256(payload)}


def method_disagreement(catalogs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted((dict(item) for item in catalogs), key=lambda item: (str(item.get("method_id", "")), str(item.get("family_catalog_id", ""))))
    assignments = [(str(item.get("method_id", "")), assignment_map(item)) for item in ordered]
    members = sorted(set().union(*(set(mapping) for _, mapping in assignments))) if assignments else []
    disagreements: list[dict[str, Any]] = []
    for member in members:
        statuses = [(method, mapping.get(member)) for method, mapping in assignments]
        normalized = [family is not None for _, family in statuses]
        if len(set(normalized)) > 1:
            disagreements.append({"record_id":member,"type":"MEMBER_VS_RESIDUAL","method_assignments":statuses})
            continue
        # If all are assigned, compare co-membership neighborhoods rather than catalog-specific IDs.
        if all(normalized):
            neighborhoods: list[tuple[str, tuple[str, ...]]] = []
            for method, mapping in assignments:
                family_id = mapping.get(member)
                peers = tuple(sorted(key for key, value in mapping.items() if value == family_id and key != member))
                neighborhoods.append((method, peers))
            if len({peers for _, peers in neighborhoods}) > 1:
                disagreements.append({"record_id":member,"type":"FAMILY_MEMBERSHIP_DISAGREEMENT","method_neighborhoods":neighborhoods})
    payload = {
        "catalog_ids": [item.get("family_catalog_id") for item in ordered],
        "method_count": len(ordered),
        "record_denominator": len(members),
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "composite_score": None,
        "authority_state": "FIXTURE_ONLY",
    }
    return {**payload, "method_disagreement_id": stable_id("SRFD.DISAGREE.", payload), "logical_hash": logical_sha256(payload)}


def run_configuration_grid(configurations: Iterable[Mapping[str, Any]], builder: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted((dict(item) for item in configurations), key=lambda item: str(item.get("configuration_id", "")))
    return [dict(builder(item)) for item in ordered]
