from __future__ import annotations

from copy import deepcopy
import unittest

from ovc.programme_genesis.topology import build_topology_from_inventory
from ovc.programme_genesis.topology_diff import TopologyDiffError, build_topology_diff, verify_topology_diff


def _model(commit: str = "a" * 40):
    return build_topology_from_inventory(
        repository="example/ovc",
        source_commit=commit,
        entries=[
            {"path": "src/ovc/example/core.py", "blob_hash": "1" * 40},
            {"path": "tests/example/test_core.py", "blob_hash": "2" * 40},
        ],
        content_by_path={
            "src/ovc/example/core.py": "VALUE = 1\n",
            "tests/example/test_core.py": "from ovc.example.core import VALUE\n",
        },
        rule_pack={"rule_pack_id": "GRT.TEST.WP10", "scan_roots": ["src/", "tests/"]},
    )


class GRTWP10DiffTests(unittest.TestCase):
    def test_same_logical_models_have_zero_changes(self) -> None:
        before = _model("a" * 40)
        after = deepcopy(before)
        after["portfolio"]["source_commit"] = "b" * 40
        diff = build_topology_diff(before, after)
        self.assertEqual(diff["change_count"], 0)
        self.assertEqual(diff["authority_effect"], "NONE_DERIVED_COMMIT_DIFF_ONLY")
        self.assertFalse(diff["programme_or_dependency_authority_changed"])
        verify_topology_diff(diff)

    def test_component_add_remove_and_state_changes_are_explicit(self) -> None:
        before = _model("a" * 40)
        after = deepcopy(before)
        after["portfolio"]["source_commit"] = "b" * 40
        original = after["components"][0]
        original["owner_programme_ids"] = ["OVC-X-v0.1"]
        original["authority_state"] = "CHANGED_REFERENCE"
        original["implementation_state"] = "SUPERSEDED"
        original["historical_state"] = "HISTORICAL"
        after["components"].append({
            "component_id": "component:new",
            "path": "src/ovc/example/new.py",
            "component_type": "PYTHON_MODULE",
            "owner_programme_ids": [],
            "authority_state": "UNRESOLVED",
            "implementation_state": "CURRENT",
            "historical_state": "CURRENT",
        })
        diff = build_topology_diff(before, after)
        types = {row["change_type"] for row in diff["changes"]}
        self.assertTrue({"NEW_COMPONENT", "CHANGED_OWNER", "CHANGED_AUTHORITY_REFERENCE", "IMPLEMENTATION_STATE_CHANGE", "SUPERSESSION_CHANGE"}.issubset(types))

    def test_dependency_and_warning_delta_use_stable_semantic_keys(self) -> None:
        before = _model("a" * 40)
        after = deepcopy(before)
        after["portfolio"]["source_commit"] = "b" * 40
        after["component_dependencies"] = []
        after["anomalies"] = list(after["anomalies"]) + [{
            "anomaly_id": "runtime-specific-id",
            "anomaly_code": "STALE_DOCUMENTATION",
            "severity": "WARNING",
            "affected_component_ids": [],
            "affected_programme_ids": [],
            "detail": "new stale documentation",
        }]
        diff = build_topology_diff(before, after)
        types = [row["change_type"] for row in diff["changes"]]
        self.assertIn("REMOVED_DEPENDENCY", types)
        self.assertIn("NEW_WARNING", types)

    def test_change_order_does_not_change_diff_identity(self) -> None:
        before = _model("a" * 40)
        after = deepcopy(before)
        after["portfolio"]["source_commit"] = "b" * 40
        after["components"] = list(reversed(after["components"]))
        after["component_dependencies"] = list(reversed(after["component_dependencies"]))
        left = build_topology_diff(before, after)
        after["components"] = list(reversed(after["components"]))
        after["component_dependencies"] = list(reversed(after["component_dependencies"]))
        right = build_topology_diff(before, after)
        self.assertEqual(left["diff_sha256"], right["diff_sha256"])

    def test_authority_bearing_input_and_tampered_diff_fail_closed(self) -> None:
        before = _model("a" * 40)
        after = deepcopy(before)
        after["authority_effect"] = "MUTATION_ALLOWED"
        with self.assertRaises(TopologyDiffError):
            build_topology_diff(before, after)
        valid = build_topology_diff(before, before)
        valid["change_count"] = 99
        with self.assertRaises(TopologyDiffError):
            verify_topology_diff(valid)


if __name__ == "__main__":
    unittest.main()
