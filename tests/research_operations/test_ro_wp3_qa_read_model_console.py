from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.console import ConsoleWriteDenied, ResearchConsole
from ovc.research_operations.qa import QARunner, required_fields_check
from ovc.research_operations.read_model import ReadModelBuilder, query_nodes


class ROWP3Tests(unittest.TestCase):
    def record(self) -> dict:
        return {
            "record_id": "record:fixture",
            "record_type": "OBSERVATION_SNAPSHOT",
            "lifecycle_state": "FROZEN",
            "authority_state": "FROZEN",
            "created_at": "2026-07-26T00:00:00Z",
            "frozen_at": "2026-07-26T00:00:00Z",
            "source_release_refs": [{"release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2"}],
            "reproducibility_state": "REPRODUCIBLE",
            "missingness": [],
            "lineage": {"parent": [], "derived_from": [], "supersedes": None, "adjudicates": []},
        }

    def test_qa_is_deterministic_and_does_not_mutate_target(self) -> None:
        target = self.record()
        before = copy.deepcopy(target)
        runner = QARunner([required_fields_check("RO-QA-001", ["record_id", "frozen_at"])])
        first = runner.run(target, target_id=target["record_id"], source_commit="abc")
        second = runner.run(target, target_id=target["record_id"], source_commit="abc")
        self.assertEqual("PASS", first.disposition)
        self.assertEqual(first.logical_sha256, second.logical_sha256)
        self.assertEqual(before, target)

    def test_qa_blocks_missing_required_field(self) -> None:
        target = self.record()
        target["frozen_at"] = None
        result = QARunner([required_fields_check("RO-QA-001", ["record_id", "frozen_at"])]).run(target, target_id=target["record_id"], source_commit="abc")
        self.assertEqual("BLOCK", result.disposition)

    def test_read_model_is_replaceable_and_logically_deterministic(self) -> None:
        builder = ReadModelBuilder()
        first = builder.build(source_commit="abc", catalogue=None, records=[self.record()])
        second = builder.build(source_commit="abc", catalogue=None, records=[self.record()])
        self.assertEqual(first.logical_sha256, second.logical_sha256)
        self.assertEqual(1, len(query_nodes(first, object_type="OBSERVATION_SNAPSHOT")))
        self.assertNotIn("created_at", first.to_dict())

    def test_console_renders_lineage_and_denies_mutation(self) -> None:
        model = ReadModelBuilder().build(source_commit="abc", catalogue=None, records=[self.record()])
        console = ResearchConsole(model)
        with tempfile.TemporaryDirectory() as tmp:
            output = console.render_html(Path(tmp) / "console.html")
            text = output.read_text(encoding="utf-8")
        self.assertIn("READ-ONLY", text)
        self.assertIn("record:fixture", text)
        self.assertIn("OPT-A.GBPUSD.DISCOVERY.2021_2023.v2", text)
        with self.assertRaises(ConsoleWriteDenied):
            console.mutate("selector", "ACTIVE")

    def test_validation_and_market_authority_are_absent(self) -> None:
        model = ReadModelBuilder().build(source_commit="abc", catalogue=None, records=[self.record()])
        capabilities = ResearchConsole(model).capabilities
        self.assertEqual("NONE", capabilities["market_classification"])
        self.assertEqual("NONE", capabilities["selector_mutation"])
        self.assertEqual("NONE", capabilities["threshold_mutation"])
        self.assertEqual("NONE", capabilities["execution"])


if __name__ == "__main__":
    unittest.main()
