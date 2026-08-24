from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/ci/pytest_shard_shadow.py"
CI_DIR = MODULE_PATH.parent
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))
SPEC = importlib.util.spec_from_file_location("pytest_shard_shadow_transport", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
shadow = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = shadow
SPEC.loader.exec_module(shadow)


class _Item:
    def __init__(self, nodeid: str) -> None:
        self.nodeid = nodeid


class PytestShardSelectionTransportTests(unittest.TestCase):
    def test_shard_command_uses_collection_filter_not_nodeid_argv(self):
        command = shadow._pytest_shard_command()
        self.assertEqual(command[:4], [sys.executable, "-m", "pytest", "tests"])
        self.assertIn("-p", command)
        self.assertIn("pytest_shard_shadow", command)
        self.assertFalse(any("::" in arg for arg in command))

    def test_collection_filter_is_exact_ordered_and_fail_closed(self):
        items = [
            _Item("tests/a.py::test_a"),
            _Item("tests/b.py::test_b"),
            _Item("tests/c.py::test_c"),
        ]
        retained, deselected = shadow._select_collected_items(
            items,
            ["tests/c.py::test_c", "tests/a.py::test_a"],
        )
        self.assertEqual(
            [item.nodeid for item in retained],
            ["tests/c.py::test_c", "tests/a.py::test_a"],
        )
        self.assertEqual(
            [item.nodeid for item in deselected],
            ["tests/b.py::test_b"],
        )
        with self.assertRaisesRegex(RuntimeError, "missing collected items"):
            shadow._select_collected_items(
                items,
                ["tests/missing.py::test_missing"],
            )
        with self.assertRaisesRegex(RuntimeError, "duplicate node ids"):
            shadow._select_collected_items(
                items,
                ["tests/a.py::test_a", "tests/a.py::test_a"],
            )

    def test_selection_file_contract_is_shadow_only_and_count_bound(self):
        payload = {
            "schema": "ovc-pytest-shard-selection/v1",
            "authority_mode": "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
            "manifest_hash": "a" * 64,
            "population_hash": "b" * 64,
            "shard_index": 0,
            "selected_item_count": 2,
            "items": ["tests/a.py::test_a", "tests/b.py::test_b"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "selection.json"
            path.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                shadow._read_selection_payload(path),
                payload["items"],
            )
            payload["selected_item_count"] = 1
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "selected_item_count mismatch"):
                shadow._read_selection_payload(path)


if __name__ == "__main__":
    unittest.main()
