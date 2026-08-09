from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FixtureStore:
    def __init__(self, root: Path):
        self.root = root
        self.manifest = self._read("manifest.json")
        required = {
            "data_classification": "SYNTHETIC_FIXTURE",
            "evidence_status": "NON_EVIDENTIARY",
            "authority_effect": "NONE",
            "mode": "FIXTURE_ONLY",
        }
        for key, expected in required.items():
            if self.manifest.get(key) != expected:
                raise ValueError(f"FIXTURE_MANIFEST_INVALID:{key}")

    def _read(self, name: str) -> dict[str, Any]:
        value = json.loads((self.root / name).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"FIXTURE_OBJECT_REQUIRED:{name}")
        return value

    def resource(self, name: str) -> dict[str, Any]:
        if name not in self.manifest["resources"]:
            raise KeyError(name)
        return self._read(self.manifest["resources"][name])

    def banner(self) -> dict[str, str]:
        return {
            "mode": "FIXTURE_ONLY",
            "data_classification": "SYNTHETIC_FIXTURE",
            "evidence_status": "NON_EVIDENTIARY",
            "authority_effect": "NONE",
        }
