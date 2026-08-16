from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REGISTRY_FILES = {
    "ontology": "ATLAS_ONTOLOGY_REGISTRY_v0_1.json",
    "predicate_authority": "ATLAS_PREDICATE_AUTHORITY_REGISTRY_v0_1.json",
    "visibility": "ATLAS_VISIBILITY_POLICY_REGISTRY_v0_1.json",
    "extractor": "ATLAS_EXTRACTOR_REGISTRY_v0_1.json",
    "resolver": "ATLAS_RESOLVER_REGISTRY_v0_1.json",
    "query_policy": "ATLAS_QUERY_POLICY_REGISTRY_v0_1.json",
    "visual_grammar": "ATLAS_VISUAL_GRAMMAR_REGISTRY_v0_1.json",
}


def load_registry_bundle(repository_root: Path | str) -> dict[str, dict[str, Any]]:
    root = Path(repository_root) / "registries/system_atlas"
    bundle: dict[str, dict[str, Any]] = {}
    for key, filename in REGISTRY_FILES.items():
        value = json.loads((root / filename).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"Atlas registry is not an object: {filename}")
        bundle[key] = value
    return bundle
