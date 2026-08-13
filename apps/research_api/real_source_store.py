from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from ovc.console_vnext.application.errors import ContractError, SourceConflict

_ALLOWED_CAPABILITIES = {"MARKET", "C1", "C2", "C2E"}


class RealSourceStore:
    """Fail-closed local reader for G4-approved owner read projections.

    This store never fetches a provider, derives scientific state, or falls back to
    fixtures. Source owners remain authoritative; this adapter only validates and
    presents already-materialised local read projections.
    """

    def __init__(self, root: Path, registry_path: Path):
        self.root = Path(root)
        self.registry_path = Path(registry_path)
        self.resource_reads = 0
        registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if registry.get("schema") != "ovc-rcn-rn-owner-read-projection-bindings/v1":
            raise ValueError("REAL_SOURCE_BINDING_REGISTRY_INVALID")
        bindings = registry.get("bindings")
        if not isinstance(bindings, list):
            raise ValueError("REAL_SOURCE_BINDINGS_LIST_REQUIRED")
        self._bindings = {str(row["capability_id"]): dict(row) for row in bindings}
        if set(self._bindings) != _ALLOWED_CAPABILITIES:
            raise ValueError("REAL_SOURCE_BINDING_CAPABILITY_SET_INVALID")

    def _path_for(self, binding: Mapping[str, Any]) -> Path:
        env_key = str(binding["environment_path"])
        configured = os.environ.get(env_key)
        return Path(configured) if configured else self.root / str(binding["default_filename"])

    @staticmethod
    def _unavailable(capability_id: str, owner_namespace: str) -> dict[str, Any]:
        return {
            "schema": "ovc-rcn-owner-read-projection/v1",
            "capability_id": capability_id,
            "owner_namespace": owner_namespace,
            "availability": "NOT_MATERIALIZED",
            "source_identity": {"source_id": "NOT_MATERIALIZED", "source_commit": "NOT_MATERIALIZED"},
            "chronology": {"status": "NOT_EVALUATED", "ordering": "FIRST_VALID_CHRONOLOGY"},
            "missingness": {"status": "NOT_EVALUATED", "evaluable_count": 0, "missing_count": 0, "denominator": 0, "reason_codes": ["UPSTREAM_OWNER_READ_PROJECTION_UNAVAILABLE"]},
            "qa": {"status": "NOT_EVALUATED", "provenance": []},
            "authority": {"read_only": True, "writes": "NONE", "validation_consumption": "LOCKED_UNCONSUMED", "source_owner_authority": "UNCHANGED"},
            "payload": {},
        }

    @staticmethod
    def _require_object(value: Any, label: str) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise ContractError(f"{label}_OBJECT_REQUIRED")
        return dict(value)

    def _validate(self, raw: Any, binding: Mapping[str, Any]) -> dict[str, Any]:
        value = self._require_object(raw, "OWNER_READ_PROJECTION")
        required = {"schema", "capability_id", "owner_namespace", "availability", "source_identity", "chronology", "missingness", "qa", "authority", "payload"}
        missing = sorted(required - set(value))
        if missing:
            raise ContractError(f"OWNER_READ_PROJECTION_MISSING_FIELDS:{missing}")
        capability_id = str(binding["capability_id"])
        if value["schema"] != "ovc-rcn-owner-read-projection/v1":
            raise ContractError("OWNER_READ_PROJECTION_SCHEMA_INVALID")
        if value["capability_id"] != capability_id:
            raise SourceConflict("OWNER_READ_PROJECTION_CAPABILITY_MISMATCH")
        if value["owner_namespace"] != binding["owner_namespace"]:
            raise SourceConflict("OWNER_READ_PROJECTION_NAMESPACE_MISMATCH")
        if value["availability"] != "AVAILABLE":
            raise ContractError("OWNER_READ_PROJECTION_AVAILABLE_REQUIRED_WHEN_FILE_PRESENT")

        source_identity = self._require_object(value["source_identity"], "SOURCE_IDENTITY")
        for key in ("source_id", "source_commit"):
            if not isinstance(source_identity.get(key), str) or not source_identity[key].strip():
                raise ContractError(f"SOURCE_IDENTITY_{key.upper()}_REQUIRED")

        chronology = self._require_object(value["chronology"], "CHRONOLOGY")
        if chronology.get("ordering") != "FIRST_VALID_CHRONOLOGY":
            raise ContractError("FIRST_VALID_CHRONOLOGY_REQUIRED")
        for key in ("first_valid_time", "cutoff"):
            if not isinstance(chronology.get(key), str) or not chronology[key].strip():
                raise ContractError(f"CHRONOLOGY_{key.upper()}_REQUIRED")

        missingness = self._require_object(value["missingness"], "MISSINGNESS")
        counts = []
        for key in ("evaluable_count", "missing_count", "denominator"):
            count = missingness.get(key)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ContractError(f"MISSINGNESS_{key.upper()}_INVALID")
            counts.append(count)
        if counts[0] + counts[1] != counts[2]:
            raise ContractError("MISSINGNESS_DENOMINATOR_MISMATCH")
        if not isinstance(missingness.get("reason_codes", []), list):
            raise ContractError("MISSINGNESS_REASON_CODES_LIST_REQUIRED")

        qa = self._require_object(value["qa"], "QA")
        if qa.get("status") not in {"PASS", "NOT_EVALUATED"}:
            raise ContractError("QA_STATUS_INVALID")
        if not isinstance(qa.get("provenance"), list):
            raise ContractError("QA_PROVENANCE_LIST_REQUIRED")

        authority = self._require_object(value["authority"], "AUTHORITY")
        expected_authority = {"read_only": True, "writes": "NONE", "validation_consumption": "LOCKED_UNCONSUMED", "source_owner_authority": "UNCHANGED"}
        for key, expected in expected_authority.items():
            if authority.get(key) != expected:
                raise ContractError(f"OWNER_READ_PROJECTION_AUTHORITY_INVALID:{key}")
        if not isinstance(value["payload"], Mapping):
            raise ContractError("OWNER_READ_PROJECTION_PAYLOAD_OBJECT_REQUIRED")
        return value

    def projection(self, capability_id: str) -> dict[str, Any]:
        capability = capability_id.upper()
        binding = self._bindings.get(capability)
        if binding is None:
            raise ContractError(f"REAL_SOURCE_CAPABILITY_NOT_BOUND:{capability}")
        path = self._path_for(binding)
        if not path.is_file():
            return self._unavailable(capability, str(binding["owner_namespace"]))
        self.resource_reads += 1
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError(f"OWNER_READ_PROJECTION_INVALID_JSON:{capability}") from exc
        return self._validate(raw, binding)

    @staticmethod
    def envelope(resource: str, projection: Mapping[str, Any], *, schema_id: str) -> dict[str, Any]:
        available = projection.get("availability") == "AVAILABLE"
        return {
            "real_source_banner": {
                "mode": "REAL_SOURCE_READ_ONLY",
                "data_classification": "OWNER_READ_PROJECTION",
                "presentation_authority": "RCN-RN-G4-PASS",
                "source_owner_authority": "UNCHANGED",
                "authority_effect": "NONE",
                "fixture_fallback": "PROHIBITED",
            },
            "schema_id": schema_id,
            "resource": resource,
            "source_identity": dict(projection["source_identity"]),
            "chronology": dict(projection["chronology"]),
            "missingness": dict(projection["missingness"]),
            "qa": dict(projection["qa"]),
            "capability": {
                "capability_id": projection["capability_id"],
                "available": available,
                "authorised": projection["capability_id"] in _ALLOWED_CAPABILITIES,
                "active": False,
                "authority_effect": "NONE",
            },
            "payload": dict(projection["payload"]),
        }

    def investigate_snapshot(self) -> dict[str, Any]:
        members = {capability: self.projection(capability) for capability in ("MARKET", "C1", "C2", "C2E")}
        return {
            "real_source_banner": {
                "mode": "REAL_SOURCE_READ_ONLY",
                "data_classification": "OWNER_READ_PROJECTION_SET",
                "presentation_authority": "RCN-RN-G4-PASS",
                "source_owner_authority": "UNCHANGED",
                "authority_effect": "NONE",
                "fixture_fallback": "PROHIBITED",
                "composition_policy": "PRESENTATION_ONLY_NO_SCIENTIFIC_SYNTHESIS",
            },
            "schema_id": "ovc-rcn-investigate-snapshot/v1",
            "resource": "investigate_snapshot",
            "source_identity": {"members": {key: value["source_identity"] for key, value in members.items()}},
            "chronology": {"status": "PER_SOURCE_ONLY", "ordering": "FIRST_VALID_CHRONOLOGY"},
            "missingness": {"status": "PER_SOURCE_ONLY"},
            "qa": {"status": "PER_SOURCE_ONLY"},
            "capability": {"capability_id": "C2", "available": members["C2"]["availability"] == "AVAILABLE", "authorised": True, "active": False, "authority_effect": "NONE"},
            "payload": {
                "market_context": members["MARKET"],
                "translation": {"c1": members["C1"]},
                "structure": {
                    "c2": members["C2"],
                    "c2e": members["C2E"],
                    "c2p": {"availability": "NOT_MATERIALIZED", "real_source_presentation": "DENIED"},
                    "c2_5": {"availability": "NOT_MATERIALIZED", "real_source_presentation": "DENIED", "event_synthesis": "PROHIBITED"},
                    "c3": {"availability": "NOT_MATERIALIZED", "real_source_presentation": "DENIED", "semantic_synthesis": "PROHIBITED"},
                },
            },
        }
