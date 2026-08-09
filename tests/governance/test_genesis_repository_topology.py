from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.topology import (
    build_repository_topology,
    build_topology_from_inventory,
    canonical_sha256,
)


ROOT = Path(__file__).resolve().parents[2]
RULE_PACK_PATH = ROOT / "registries/governance/genesis_repository_topology/GRT_TOPOLOGY_RULE_PACK_v0_1.json"


def _fixture_model(entries, content):
    return build_topology_from_inventory(
        repository="example/ovc",
        source_commit="a" * 40,
        entries=entries,
        content_by_path=content,
        rule_pack={"rule_pack_id": "GRT.TEST.v0.1", "scan_roots": ["src/", "contracts/", "registries/"]},
    )


def test_topology_identity_is_independent_of_inventory_order() -> None:
    entries = [
        {"path": "src/ovc/example/core.py", "blob_hash": "1" * 40},
        {"path": "contracts/example/EXAMPLE.md", "blob_hash": "2" * 40},
    ]
    content = {
        "src/ovc/example/core.py": "from __future__ import annotations\n",
        "contracts/example/EXAMPLE.md": 'programme_id: OVC-EXAMPLE-v0.1\nsource: src/ovc/example/core.py\n',
    }
    left = _fixture_model(entries, content)
    right = _fixture_model(list(reversed(entries)), content)
    assert left["topology_sha256"] == right["topology_sha256"]
    assert left["authority_effect"] == "NONE_DERIVED_REPLACEABLE_READ_MODEL"
    assert all(edge["authority_effect"] == "NONE" for edge in left["component_dependencies"])


def test_inferred_hard_programme_dependency_is_blocker() -> None:
    entries = [
        {"path": "registries/governance/dependencies.json", "blob_hash": "3" * 40},
    ]
    content = {
        "registries/governance/dependencies.json": json.dumps({
            "programme_id": "OVC-EXAMPLE-v0.1",
            "edges": [{
                "edge_type": "REQUIRES",
                "from_node": "OVC-A-v0.1",
                "to_node": "OVC-B-v0.1",
                "hardness": "HARD",
                "status": "PROPOSED",
                "source_kind": "INFERRED",
            }],
        }),
    }
    model = _fixture_model(entries, content)
    blockers = [row for row in model["anomalies"] if row["anomaly_code"] == "INFERRED_HARD_DEPENDENCY"]
    assert len(blockers) == 1
    assert blockers[0]["severity"] == "BLOCKER"
    assert blockers[0]["authority_effect"] == "NONE_ADVISORY_ONLY"


def test_unknown_implementation_owner_stays_unresolved() -> None:
    model = _fixture_model(
        [{"path": "src/ovc/unowned/module.py", "blob_hash": "4" * 40}],
        {"src/ovc/unowned/module.py": "VALUE = 1\n"},
    )
    component = model["components"][0]
    assert component["owner_programme_id"] is None
    assert component["owner_programme_ids"] == []
    assert any(row["anomaly_code"] == "IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER" for row in model["anomalies"])


def test_rule_pack_has_no_manual_owner_map_or_authority() -> None:
    rules = json.loads(RULE_PACK_PATH.read_text(encoding="utf-8"))
    assert rules["authority_effect"] == "NONE_DERIVED_RULES_ONLY"
    assert "owner_map" not in rules
    assert rules["hard_dependency_policy"].startswith("ONLY_SOURCE_EXPLICIT")
    assert rules["health_score_policy"].startswith("NO_OPAQUE_SCORE")


def test_repository_clean_rebuild_is_deterministic() -> None:
    rules = json.loads(RULE_PACK_PATH.read_text(encoding="utf-8"))
    first = build_repository_topology(ROOT, rule_pack=rules)
    second = build_repository_topology(ROOT, rule_pack=rules)
    assert first["topology_sha256"] == second["topology_sha256"]
    assert first["portfolio"] == second["portfolio"]
    assert first["health_summary"]["opaque_score"] is None
    assert first["portfolio"]["component_count"] > 0
    assert first["portfolio"]["programme_count"] > 0
    assert all(edge["evidence_class"] != "INFERRED" or edge["authority_effect"] == "NONE" for edge in first["component_dependencies"])
    assert canonical_sha256(first["build_metadata"]) == canonical_sha256(second["build_metadata"])
