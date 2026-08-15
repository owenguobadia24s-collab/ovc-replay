from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .core import RCCRValidationError, canonical_json_bytes, logical_identity, validate_canonical_object

DESIGN_STATES = {"YES", "NO", "UNKNOWN"}
IMPLEMENTATION_STATES = {"YES", "PARTIAL", "NO", "UNKNOWN"}
AVAILABILITY_STATES = {"YES", "NO", "UNKNOWN"}
QUALIFICATION_STATES = {"QUALIFIED_FOR_DECLARED_USE", "NOT_QUALIFIED", "UNKNOWN"}
AUTHORITY_STATES = {"AUTHORISED_FOR_DECLARED_USE", "NOT_AUTHORISED", "UNKNOWN"}
ACTIVATION_STATES = {"ACTIVE_FOR_DECLARED_USE", "INACTIVE", "UNKNOWN"}

PLANE_ENUMS = {
    "design": DESIGN_STATES,
    "implementation": IMPLEMENTATION_STATES,
    "availability": AVAILABILITY_STATES,
    "qualification": QUALIFICATION_STATES,
    "authority": AUTHORITY_STATES,
    "activation": ACTIVATION_STATES,
}


@dataclass(frozen=True)
class CapabilityBinding:
    capability_id: str
    owner_programme: str
    responsibility: str
    design: str
    implementation: str
    availability: str
    qualification: str
    authority: str
    activation: str
    owner_state_digest: str
    first_valid_time: str
    source_refs: tuple[str, ...]
    active_stack_classification: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "owner_programme": self.owner_programme,
            "responsibility": self.responsibility,
            "design": self.design,
            "implementation": self.implementation,
            "availability": self.availability,
            "qualification": self.qualification,
            "authority": self.authority,
            "activation": self.activation,
            "owner_state_digest": self.owner_state_digest,
            "first_valid_time": self.first_valid_time,
            "source_refs": list(self.source_refs),
            "active_stack_classification": self.active_stack_classification,
            "authority_effect": "NONE",
        }


class CapabilityBindingResolver:
    """Resolve only exact owner-bound capability records into six orthogonal maturity planes."""

    def __init__(self, catalog: Iterable[Mapping[str, Any]]):
        self._catalog: dict[str, dict[str, Any]] = {}
        for raw in catalog:
            item = deepcopy(dict(raw))
            capability_id = item.get("capability_id")
            if not isinstance(capability_id, str) or not capability_id:
                raise RCCRValidationError("CAPABILITY_EXACT_ID_REQUIRED", str(capability_id))
            if capability_id in self._catalog:
                raise RCCRValidationError("DUPLICATE_CAPABILITY_ID", capability_id)
            self._catalog[capability_id] = item

    def resolve(self, capability_id: str) -> CapabilityBinding:
        if capability_id not in self._catalog:
            raise RCCRValidationError("CAPABILITY_NOT_FOUND_EXACT_ID", capability_id)
        item = deepcopy(self._catalog[capability_id])
        if item.get("protected") is True or str(item.get("protection_class", "")).upper() == "VALIDATION":
            raise RCCRValidationError("PROTECTED_CAPABILITY_SOURCE_DENIED", capability_id)
        for field in ("owner_programme", "responsibility", "owner_state_digest", "first_valid_time", "source_refs"):
            if item.get(field) in (None, ""):
                raise RCCRValidationError("CAPABILITY_OWNER_METADATA_INCOMPLETE", f"{capability_id}:{field}")
        for plane, allowed in PLANE_ENUMS.items():
            value = item.get(plane)
            if value not in allowed:
                raise RCCRValidationError("UNKNOWN_CAPABILITY_PLANE_STATE", f"{capability_id}:{plane}={value}")
        return CapabilityBinding(
            capability_id=capability_id,
            owner_programme=str(item["owner_programme"]),
            responsibility=str(item["responsibility"]),
            design=str(item["design"]),
            implementation=str(item["implementation"]),
            availability=str(item["availability"]),
            qualification=str(item["qualification"]),
            authority=str(item["authority"]),
            activation=str(item["activation"]),
            owner_state_digest=str(item["owner_state_digest"]),
            first_valid_time=str(item["first_valid_time"]),
            source_refs=tuple(str(ref) for ref in item["source_refs"]),
            active_stack_classification=item.get("active_stack_classification"),
        )


class CapabilityFrontierCompiler:
    """Compile a deterministic requirement-relevant frontier without collapsing maturity planes."""

    def compile(
        self,
        *,
        resolved_bindings: Iterable[CapabilityBinding],
        relevant_capability_ids: Iterable[str],
        evaluation_cutoff: str,
        scope: Iterable[str],
        data_bindings: Iterable[Mapping[str, Any]] = (),
        method_bindings: Iterable[Mapping[str, Any]] = (),
        authority_bindings: Iterable[Mapping[str, Any]] = (),
        protected_bindings: Iterable[Mapping[str, Any]] = (),
        stack_projections: Mapping[str, Mapping[str, Any]] | None = None,
        first_valid_time: str | None = None,
        unrelated_main_sha: str | None = None,
    ) -> dict[str, Any]:
        del unrelated_main_sha  # physical repository movement is not semantic frontier identity.
        relevant = set(str(item) for item in relevant_capability_ids)
        bindings = [binding for binding in resolved_bindings if binding.capability_id in relevant]
        by_id = {binding.capability_id: binding for binding in bindings}
        missing = sorted(relevant - set(by_id))
        unresolved: list[dict[str, Any]] = [
            {"kind": "MISSING_RELEVANT_CAPABILITY", "capability_id": capability_id, "authority_effect": "NONE"}
            for capability_id in missing
        ]
        projections = stack_projections or {}
        capability_rows: list[dict[str, Any]] = []
        provenance: set[str] = set()
        court_record: set[str] = set()
        for capability_id in sorted(by_id):
            binding = by_id[capability_id]
            row = binding.as_dict()
            capability_rows.append(row)
            provenance.update(binding.source_refs)
            provenance.add(binding.owner_state_digest)
            court_record.add(f"OWNER_STATE:{capability_id}:{binding.owner_state_digest}")
            projection = projections.get(capability_id)
            if projection:
                projection_ref = str(projection.get("projection_ref", ""))
                classification = projection.get("active_stack_classification")
                if projection_ref:
                    provenance.add(projection_ref)
                    court_record.add(f"STACK_PROJECTION:{capability_id}:{projection_ref}")
                if classification and classification != binding.active_stack_classification:
                    unresolved.append(
                        {
                            "kind": "OWNER_STACK_PROJECTION_DISCREPANCY",
                            "capability_id": capability_id,
                            "owner_active_stack_classification": binding.active_stack_classification,
                            "projected_active_stack_classification": classification,
                            "projection_ref": projection_ref,
                            "resolution": "PRESERVE_BOTH_STOP_INFERENCE",
                            "authority_effect": "NONE",
                        }
                    )
            unknown_planes = [plane for plane in PLANE_ENUMS if getattr(binding, plane) == "UNKNOWN"]
            if unknown_planes:
                unresolved.append(
                    {
                        "kind": "CAPABILITY_PLANE_UNKNOWN",
                        "capability_id": capability_id,
                        "planes": sorted(unknown_planes),
                        "authority_effect": "NONE",
                    }
                )
        def canonical_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
            copied = [deepcopy(dict(row)) for row in rows]
            copied.sort(key=lambda row: canonical_json_bytes(row))
            return copied
        authority_rows = canonical_rows(authority_bindings)
        for row in authority_rows:
            if row.get("authority_effect") not in (None, "NONE"):
                raise RCCRValidationError("FRONTIER_AUTHORITY_EFFECT_DENIED", str(row.get("authority_effect")))
        all_fvt = [binding.first_valid_time for binding in bindings]
        effective_fvt = first_valid_time or (max(all_fvt) if all_fvt else evaluation_cutoff)
        record: dict[str, Any] = {
            "schema_version": "0.1",
            "capability_frontier_id": "PENDING",
            "evaluation_cutoff": evaluation_cutoff,
            "scope": sorted(set(str(item) for item in scope)),
            "court_record_provenance": sorted(court_record),
            "capability_bindings": capability_rows,
            "data_bindings": canonical_rows(data_bindings),
            "method_bindings": canonical_rows(method_bindings),
            "authority_bindings": authority_rows,
            "protected_bindings": canonical_rows(protected_bindings),
            "unresolved_bindings": sorted(unresolved, key=canonical_json_bytes),
            "provenance_refs": sorted(provenance),
            "first_valid_time": effective_fvt,
            "authority_effect": "NONE",
        }
        record["capability_frontier_id"] = logical_identity("ResearchCapabilityFrontier", record)
        validate_canonical_object("ResearchCapabilityFrontier", record)
        return record


def binding_state_digest(binding: Mapping[str, Any]) -> str:
    material = deepcopy(dict(binding))
    material.pop("owner_state_digest", None)
    return hashlib.sha256(canonical_json_bytes(material)).hexdigest()
