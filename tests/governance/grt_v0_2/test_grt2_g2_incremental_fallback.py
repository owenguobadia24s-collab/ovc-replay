from __future__ import annotations

import unittest

from ovc.programme_genesis.grt_v0_2.incremental import build_incremental_graph
from ovc.programme_genesis.grt_v0_2.reference import build_reference_graph


class GRT2G2IncrementalFallbackTests(unittest.TestCase):
    def test_incremental_fallback_is_semantically_identical_to_reference(self) -> None:
        tree = "1" * 40
        components = [
            {"path": "src/a.py", "content_hash": "2" * 40, "component_type": "file"},
            {"path": "tests/test_a.py", "content_hash": "3" * 40, "component_type": "file"},
        ]
        reference = build_reference_graph(tree_hash=tree, components=components)
        incremental = build_incremental_graph(
            tree_hash=tree,
            components=components,
            changed_paths=["src/a.py"],
        )
        self.assertEqual(incremental["strategy"], "FULL_REFERENCE_FALLBACK")
        self.assertEqual(incremental["reference_canonical_hash"], reference["canonical_hash"])
        self.assertEqual(incremental["semantic_graph"], reference)
        self.assertEqual(incremental["authority_effect"], "NONE_INCREMENTAL_SHADOW_ONLY")


if __name__ == "__main__":
    unittest.main()
