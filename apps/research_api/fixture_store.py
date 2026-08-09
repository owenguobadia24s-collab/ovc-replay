from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FixtureStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.resource_reads = 0
        self._manifest = self._read_json(self.root / "manifest.json", count=False)
        required = {
            "pack_id": "OVC-RC-VNEXT-CONSOLE-FIXTURE-PACK-v0.1",
            "data_classification": "SYNTHETIC_FIXTURE",
            "evidence_status": "NON_EVIDENTIARY",
            "authority_effect": "NONE",
            "mode": "FIXTURE_ONLY",
            "display_banner_required": True,
        }
        for key, expected in required.items():
            if self._manifest.get(key) != expected:
                raise ValueError(f"FIXTURE_MANIFEST_INVALID:{key}")

    def _read_json(self, path: Path, *, count: bool = True) -> dict[str, Any]:
        if count:
            self.resource_reads += 1
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("FIXTURE_RESOURCE_OBJECT_REQUIRED")
        return payload

    def resource(self, name: str) -> dict[str, Any]:
        resources = self._manifest.get("resources", {})
        relative = resources.get(name)
        if not isinstance(relative, str):
            raise ValueError(f"FIXTURE_RESOURCE_NOT_REGISTERED:{name}")
        return self._read_json(self.root / relative)

    def identity(self) -> dict[str, Any]:
        return dict(self._manifest["source_identity"])

    def capability(self, capability_id: str) -> dict[str, Any]:
        for row in self.resource("capabilities").get("items", []):
            if row.get("capability_id") == capability_id:
                return dict(row)
        return {
            "capability_id": capability_id,
            "display_name": capability_id,
            "implementation_state": "NOT_IMPLEMENTED",
            "source_materialization": "NOT_MATERIALIZED",
            "source_compatibility": "UNKNOWN",
            "available": False,
            "authorised": False,
            "active": False,
            "authority_effect": "NONE",
            "source_identity": self.identity(),
            "blockers": [{"reason_code": "UPSTREAM_READ_MODEL_GAP"}],
            "dependencies": [],
            "last_verified_commit": self.identity()["commit"],
        }

    def banner(self) -> dict[str, str]:
        return {
            "mode": "FIXTURE_ONLY",
            "data_classification": "SYNTHETIC_FIXTURE",
            "evidence_status": "NON_EVIDENTIARY",
            "authority_effect": "NONE",
        }

    def envelope(self, resource: str, payload: Any, *, schema_id: str, capability_id: str) -> dict[str, Any]:
        capability = self.capability(capability_id)
        return {
            "fixture_banner": self.banner(),
            "schema_id": schema_id,
            "resource": resource,
            "source_identity": self.identity(),
            "capability": {
                "capability_id": capability["capability_id"],
                "available": capability["available"],
                "authorised": capability["authorised"],
                "active": capability["active"],
                "authority_effect": capability["authority_effect"],
            },
            "payload": payload,
        }
