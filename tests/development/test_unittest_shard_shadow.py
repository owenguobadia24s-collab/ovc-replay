from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/ci/unittest_shard_shadow.py"
CI_DIR = MODULE_PATH.parent
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))
SPEC = importlib.util.spec_from_file_location("unittest_shard_shadow", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
shadow = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = shadow
SPEC.loader.exec_module(shadow)


class UnittestShardShadowTests(unittest.TestCase):
    def records(self):
        return [
            shadow.CaseRecord("tests/a.py::A::test_1", "tests/a.py", 0),
            shadow.CaseRecord("tests/heavy0.py::H0::test_a", "tests/heavy0.py", 1),
            shadow.CaseRecord("tests/b.py::B::test_1", "tests/b.py", 2),
            shadow.CaseRecord("tests/heavy1.py::H1::test_a", "tests/heavy1.py", 3),
            shadow.CaseRecord("tests/c.py::C::test_1", "tests/c.py", 4),
            shadow.CaseRecord("tests/heavy2.py::H2::test_a", "tests/heavy2.py", 5),
            shadow.CaseRecord("tests/d.py::D::test_1", "tests/d.py", 6),
            shadow.CaseRecord("tests/heavy3.py::H3::test_a", "tests/heavy3.py", 7),
        ]

    def test_assignment_is_deterministic_exact_one_and_preserves_record_order(self):
        heavy = {
            "tests/heavy0.py": 0,
            "tests/heavy1.py": 1,
            "tests/heavy2.py": 2,
            "tests/heavy3.py": 3,
        }
        first = shadow.assign_records(self.records(), shard_count=4, heavy_path_to_shard=heavy)
        second = shadow.assign_records(self.records(), shard_count=4, heavy_path_to_shard=heavy)
        self.assertEqual(first, second)
        flattened = [record.key for shard in first for record in shard]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(set(flattened), {record.key for record in self.records()})
        for shard in first:
            ordinals = [record.ordinal for record in shard]
            self.assertEqual(ordinals, sorted(ordinals))

    def test_each_heavy_path_is_isolated_to_declared_shard(self):
        heavy = {
            "tests/heavy0.py": 0,
            "tests/heavy1.py": 1,
            "tests/heavy2.py": 2,
            "tests/heavy3.py": 3,
        }
        shards = shadow.assign_records(self.records(), shard_count=4, heavy_path_to_shard=heavy)
        for path, index in heavy.items():
            self.assertTrue(any(record.source_path == path for record in shards[index]))
            for other_index, shard in enumerate(shards):
                if other_index != index:
                    self.assertFalse(any(record.source_path == path for record in shard))

    def test_missing_configured_heavy_path_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "configured heavy paths missing"):
            shadow.assign_records(
                self.records(),
                shard_count=4,
                heavy_path_to_shard={"tests/not-present.py": 0},
            )

    def test_duplicate_case_identity_fails_closed(self):
        records = self.records()
        records.append(shadow.CaseRecord(records[0].key, "tests/z.py", 99))
        with self.assertRaisesRegex(RuntimeError, "duplicate case identities"):
            shadow.assign_records(records, shard_count=4, heavy_path_to_shard={})

    def test_empty_shard_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "empty shard"):
            shadow.assign_records(
                [shadow.CaseRecord("tests/a.py::A::test_1", "tests/a.py", 0)],
                shard_count=4,
                heavy_path_to_shard={},
            )


if __name__ == "__main__":
    unittest.main()
