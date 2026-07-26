from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.console_overview import (
    HEALTH_DOMAIN_ORDER,
    normalize_health_status,
)
from ovc.research_operations.console_overview_candidate import CandidateOverviewProjectionBuilder
from ovc.research_operations.read_model import ReadModelNode, ResearchReadModel

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "research_operations" / "research_console_v0_3" / "RC_WP2_OVERVIEW_SOURCE_READ_MODEL.json"
PACKET = ROOT / "docs" / "releases" / "research-console-v0-3" / "rc-wp2" / "RC_WP2_IMPLEMENTATION_PACKET.json"
REGISTRY = ROOT / "registries" / "research_operations" / "RESEARCH_CONSOLE_OVERVIEW_PROJECTION_REGISTRY_v0_3.yaml"
SCHEMA = ROOT / "schemas" / "research_operations" / "research_console_overview_projection_v0_3.schema.json"


def load_model(path: Path = FIXTURE) -> ResearchReadModel:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ResearchReadModel(
        schema=raw["schema"],
        source_commit=raw["source_commit"],
        catalogue_sha256=raw.get("catalogue_sha256"),
        nodes=tuple(
            ReadModelNode(
                object_id=node["object_id"],
                object_type=node["object_type"],
                authority=node["authority"],
                status=node["status"],
                source_refs=tuple(node.get("source_refs", [])),
                payload=dict(node.get("payload", {})),
            )
            for node in raw.get("nodes", [])
        ),
        health=tuple(raw.get("health", [])),
        logical_sha256=raw["logical_sha256"],
    )


class RCWP2V03OverviewHealthTests(unittest.TestCase):
    def test_projection_is_deterministic_across_input_order(self) -> None:
        model = load_model()
        reversed_model = ResearchReadModel(
            schema=model.schema,
            source_commit=model.source_commit,
            catalogue_sha256=model.catalogue_sha256,
            nodes=tuple(reversed(model.nodes)),
            health=tuple(reversed(model.health)),
            logical_sha256=model.logical_sha256,
        )
        first = CandidateOverviewProjectionBuilder().build(model)
        second = CandidateOverviewProjectionBuilder().build(reversed_model)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(len(first.logical_sha256), 64)

    def test_health_domains_are_complete_and_research_records_fail_honestly(self) -> None:
        projection = CandidateOverviewProjectionBuilder().build(load_model())
        domains = {item.domain: item for item in projection.health_domains}
        self.assertEqual(tuple(item.domain for item in projection.health_domains), HEALTH_DOMAIN_ORDER)
        self.assertEqual(domains["RESEARCH_RECORDS"].status, "NOT_EVALUATED")
        self.assertEqual(domains["RESEARCH_RECORDS"].progress, 0.0)
        self.assertNotEqual(projection.summary_status, "PASS")
        self.assertIn("No research-record health claim", domains["RESEARCH_RECORDS"].consequence)

    def test_explicit_health_signals_drive_domain_consequence(self) -> None:
        projection = CandidateOverviewProjectionBuilder().build(load_model())
        domains = {item.domain: item for item in projection.health_domains}
        self.assertEqual(domains["DATA"].status, "PASS")
        self.assertEqual(domains["ARTIFACTS"].status, "WARN")
        self.assertEqual(domains["QA"].status, "PASS")
        self.assertEqual(domains["READ_MODEL"].status, "PASS")
        self.assertEqual(domains["REPOSITORY"].status, "PASS")
        self.assertEqual(domains["SEMANTIC"].status, "NOT_EVALUATED")

    def test_unknown_health_status_fails_closed(self) -> None:
        model = load_model()
        unknown = ResearchReadModel(
            schema=model.schema,
            source_commit=model.source_commit,
            catalogue_sha256=model.catalogue_sha256,
            nodes=model.nodes,
            health=model.health + ({"domain": "DATA", "code": "NEW", "status": "SOMETHING_NEW", "object_id": "X", "detail": "Unknown"},),
            logical_sha256=model.logical_sha256,
        )
        projection = CandidateOverviewProjectionBuilder().build(unknown)
        data = next(item for item in projection.health_domains if item.domain == "DATA")
        self.assertEqual(data.status, "BLOCK")
        self.assertEqual(normalize_health_status("SOMETHING_NEW"), "BLOCK")

    def test_lifecycle_vocabulary_does_not_become_false_health_block(self) -> None:
        projection = CandidateOverviewProjectionBuilder().build(load_model())
        attention_ids = {item["object_id"] for item in projection.attention}
        self.assertNotIn("RELEASE.FIXTURE.DEV", attention_ids)
        self.assertNotIn("SESSION.FIXTURE.001", attention_ids)
        self.assertNotIn("RECORD.FIXTURE.001", attention_ids)
        self.assertIn("HEALTH.RESEARCH_RECORDS", attention_ids)

    def test_projection_contains_source_bound_overview_summaries(self) -> None:
        projection = CandidateOverviewProjectionBuilder().build(load_model())
        self.assertEqual(projection.metrics["indexed_objects"], 6)
        self.assertEqual(projection.metrics["release_objects"], 1)
        self.assertEqual(projection.metrics["gate_objects"], 1)
        self.assertEqual(projection.metrics["session_objects"], 1)
        self.assertEqual(projection.releases[0]["object_id"], "RELEASE.FIXTURE.DEV")
        self.assertEqual(projection.gates[0]["object_id"], "GATE.RC_G1")
        self.assertEqual(projection.sessions[0]["object_id"], "SESSION.FIXTURE.001")
        self.assertIn("read-model:" + ("a" * 64), projection.source_refs)

    def test_candidate_builder_command_writes_non_active_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "overview.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_research_console_overview.py"),
                    "--read-model",
                    str(FIXTURE),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("CANDIDATE_ONLY_PENDING_RC_G2", result.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "ovc-research-console-overview-projection/v0.3")
            self.assertEqual(payload["health_domains"][4]["status"], "NOT_EVALUATED")

    def test_schema_registry_packet_and_activation_boundary(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        registry = REGISTRY.read_text(encoding="utf-8")
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        home = (ROOT / "apps" / "research_console" / "Home.py").read_text(encoding="utf-8")
        shell = (ROOT / "apps" / "research_console" / "shell.py").read_text(encoding="utf-8")
        self.assertEqual(schema["properties"]["schema"]["const"], "ovc-research-console-overview-projection/v0.3")
        self.assertIn("active_console_consumption: DENIED_PENDING_RC_G2", registry)
        self.assertIn("research_records_empty_progress: 0", registry)
        self.assertEqual(packet["authority"], "CANDIDATE_PROJECTION_IMPLEMENTATION_ONLY")
        self.assertEqual(packet["disposition"], "COMPLETE_RC_G2_V0_3_REVIEW_READY")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertNotIn("console_overview_candidate", home)
        self.assertNotIn("console_overview_candidate", shell)


if __name__ == "__main__":
    unittest.main()
