from __future__ import annotations

import json
import py_compile
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.research_operations.console_research import ResearchContext, ResearchWorkspaceProjectionBuilder
from ovc.research_operations.console_research_candidate import build_candidate, load_source_bundle

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "research_operations" / "research_console_v0_3" / "RC_WP3_RESEARCH_SOURCE_RECORDS.json"
PACKET = ROOT / "docs" / "releases" / "research-console-v0-3" / "rc-wp3" / "RC_WP3_IMPLEMENTATION_PACKET.json"
REGISTRY = ROOT / "registries" / "research_operations" / "RESEARCH_CONSOLE_RESEARCH_PROJECTION_REGISTRY_v0_3.yaml"


class RCWP3V03ResearchWorkspaceTests(unittest.TestCase):
    def test_prospective_projection_physically_withholds_post_cutoff_state(self) -> None:
        projection = build_candidate(FIXTURE, cutoff_mode="PROSPECTIVE").to_dict()
        self.assertEqual(projection["context"]["cutoff_mode"], "PROSPECTIVE")
        self.assertTrue(projection["replay"])
        self.assertTrue(all(item["visibility_phase"] == "PRE_CUTOFF" for item in projection["replay"]))
        self.assertTrue(all(item["visibility_phase"] == "PRE_CUTOFF" for item in projection["evidence"]))
        self.assertNotIn("CONTRADICTION", {item["evidence_role"] for item in projection["evidence"]})
        self.assertTrue(all(item["time"] <= projection["context"]["selected_time"] for item in projection["replay"]))

    def test_review_projection_labels_later_path_and_contradiction(self) -> None:
        projection = build_candidate(FIXTURE, cutoff_mode="REVIEW").to_dict()
        later_replay = [item for item in projection["replay"] if item["visibility_phase"] == "POST_CUTOFF_REVIEW"]
        later_evidence = [item for item in projection["evidence"] if item["visibility_phase"] == "POST_CUTOFF_REVIEW"]
        self.assertTrue(later_replay)
        self.assertEqual({item["evidence_role"] for item in later_evidence}, {"CONTRADICTION"})
        self.assertTrue(all(item["cutoff_locked"] is False for item in projection["replay"]))

    def test_projection_is_deterministic_under_record_reordering(self) -> None:
        raw = load_source_bundle(FIXTURE)
        context = ResearchContext(**raw["context"])
        builder = ResearchWorkspaceProjectionBuilder()
        first = builder.build(source_commit=raw["source_commit"], records=raw["records"], context=context)
        second = builder.build(source_commit=raw["source_commit"], records=reversed(raw["records"]), context=context)
        self.assertEqual(first.logical_sha256, second.logical_sha256)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_queue_preserves_due_censored_and_incident_consequences(self) -> None:
        projection = build_candidate(FIXTURE).to_dict()
        queue_types = {item["queue_type"] for item in projection["queue"]}
        self.assertIn("DUE_REALIZATION", queue_types)
        self.assertIn("CENSORED_REALIZATION", queue_types)
        self.assertIn("INCIDENT", queue_types)
        self.assertTrue(all(item["source_refs"] for item in projection["queue"]))
        self.assertEqual(projection["summary_status"], "WARN")

    def test_context_mismatch_produces_no_research_claim(self) -> None:
        raw = load_source_bundle(FIXTURE)
        context = ResearchContext(
            instrument="XAUUSD",
            release_id=raw["context"]["release_id"],
            clock=raw["context"]["clock"],
            price_side=raw["context"]["price_side"],
            selected_time=raw["context"]["selected_time"],
            cutoff_mode="PROSPECTIVE",
        )
        projection = ResearchWorkspaceProjectionBuilder().build(
            source_commit=raw["source_commit"], records=raw["records"], context=context
        )
        self.assertEqual(projection.summary_status, "NOT_EVALUATED")
        self.assertEqual(projection.brief["status"], "NOT_MATERIALIZED")
        self.assertEqual(projection.replay, ())
        self.assertEqual(projection.evidence, ())

    def test_unknown_evidence_role_fails_closed(self) -> None:
        raw = load_source_bundle(FIXTURE)
        records = deepcopy(raw["records"])
        evidence = next(item for item in records if item["record_type"] == "EVIDENCE_ITEM")
        evidence["record_id"] = "ro:evidence_item:5555555555555555555555555555555555555555555555555555555555555555"
        evidence["payload"]["evidence_role"] = "SURPRISE_ROLE"
        context = ResearchContext(**raw["context"])
        projection = ResearchWorkspaceProjectionBuilder().build(
            source_commit=raw["source_commit"], records=records, context=context
        )
        unresolved = next(item for item in projection.evidence if item["evidence_id"].endswith("5555"))
        self.assertEqual(unresolved["evidence_role"], "UNRESOLVED")
        self.assertEqual(unresolved["presentation_status"], "BLOCK")
        self.assertEqual(projection.summary_status, "BLOCK")

    def test_invalid_cutoff_mode_is_rejected(self) -> None:
        raw = load_source_bundle(FIXTURE)
        context = ResearchContext(
            instrument=raw["context"]["instrument"],
            release_id=raw["context"]["release_id"],
            clock=raw["context"]["clock"],
            price_side=raw["context"]["price_side"],
            selected_time=raw["context"]["selected_time"],
            cutoff_mode="HINDSIGHT",
        )
        with self.assertRaises(ValueError):
            ResearchWorkspaceProjectionBuilder().build(
                source_commit=raw["source_commit"], records=raw["records"], context=context
            )

    def test_candidate_builder_and_schema_are_bounded_and_compile(self) -> None:
        for path in (
            ROOT / "src" / "ovc" / "research_operations" / "console_research.py",
            ROOT / "src" / "ovc" / "research_operations" / "console_research_candidate.py",
            ROOT / "scripts" / "build_research_console_research.py",
        ):
            py_compile.compile(str(path), doraise=True)
        schema = json.loads(
            (ROOT / "schemas" / "research_operations" / "research_console_research_projection_v0_3.schema.json").read_text()
        )
        self.assertEqual(schema["properties"]["schema"]["const"], "ovc-research-console-research-projection/v0.3")
        home = (ROOT / "apps" / "research_console" / "Home.py").read_text(encoding="utf-8")
        shell = (ROOT / "apps" / "research_console" / "shell.py").read_text(encoding="utf-8")
        self.assertNotIn("research_candidate.json", home)
        self.assertNotIn("console_research_candidate", shell)

    def test_registry_and_packet_preserve_authority_boundary(self) -> None:
        registry = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("status: IMPLEMENTED_CANDIDATE_PENDING_RC_G3", registry)
        self.assertIn("active_live_research_surface: DENIED_PENDING_RC_G3", registry)
        self.assertIn("prospective_mode: PHYSICALLY_EXCLUDE_POST_CUTOFF_RECORDS_AND_PATH_POINTS", registry)
        self.assertIn("research_write: DENIED_PENDING_SEPARATE_GATE", registry)
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        self.assertEqual(packet["work_package"], "RC-WP3-v0.3")
        self.assertEqual(packet["baseline_commit"], "cd0327e11084d19ce8b51fea67c6cfa3eb00c502")
        self.assertEqual(packet["authority"], "CANDIDATE_RESEARCH_PROJECTION_IMPLEMENTATION_ONLY")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertEqual(packet["disposition"], "COMPLETE_RC_G3_V0_3_REVIEW_READY")
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))


if __name__ == "__main__":
    unittest.main()
