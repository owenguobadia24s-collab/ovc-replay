from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from ovc.development.skills.materialisation import (
    PlanMaterialisationError,
    build_plan_source_ref,
    capability_ids_from_registry,
    materialise_programme,
    verify_materialisation_freshness,
    verify_plan_source,
)
from ovc.development.skills.orchestration import build_packet_eligibility_record
from ovc.development.skills.registry import validate_against_schema


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "fixtures/development_skills/plan_packet_materialisation_v0_1.json"
SCHEMA_ROOT = ROOT / "schemas/development/skills"
CAPABILITY_REGISTRY = ROOT / "registries/development/skills/capabilities_v0_1.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PlanPacketMaterialisationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load_json(FIXTURE_PATH)
        self.capability_registry = load_json(CAPABILITY_REGISTRY)
        self.capability_ids = capability_ids_from_registry(self.capability_registry)

    def source_ref(self, programme: dict) -> dict:
        source = self.fixture["source_basis"][programme["plan_index"]]
        return build_plan_source_ref(
            plan_id=source["plan_id"],
            plan_version=source["plan_version"],
            source_ref=source["source_ref"],
            source_sha256=source["source_sha256"],
        )

    def materialise(self, programme: dict):
        return materialise_programme(
            programme_id=programme["programme_id"],
            baseline_main="a" * 40,
            plan_source_ref=self.source_ref(programme),
            packets=programme["packets"],
            gates=programme["gates"],
            known_capability_ids=self.capability_ids,
        )

    def test_representative_dsai_c2p_esli_plans_materialise_and_validate(self) -> None:
        schema_source = load_json(SCHEMA_ROOT / "plan_source_ref_v0_1.schema.json")
        schema_capability = load_json(SCHEMA_ROOT / "capability_requirement_v0_1.schema.json")
        schema_packet = load_json(SCHEMA_ROOT / "packet_manifest_v0_1.schema.json")
        schema_gate = load_json(SCHEMA_ROOT / "packet_gate_manifest_v0_1.schema.json")
        schema_programme = load_json(SCHEMA_ROOT / "programme_manifest_v0_1.schema.json")
        schema_receipt = load_json(SCHEMA_ROOT / "plan_packet_materialisation_receipt_v0_1.schema.json")

        styles = []
        for programme in self.fixture["programmes"]:
            styles.append(programme["style"])
            source_ref = self.source_ref(programme)
            manifest, graph, receipt = self.materialise(programme)
            validate_against_schema(source_ref, schema_source)
            validate_against_schema(manifest, schema_programme)
            validate_against_schema(receipt, schema_receipt)
            for packet in manifest["packets"]:
                validate_against_schema(packet, schema_packet)
                for requirement in packet["capability_requirements"]:
                    validate_against_schema(requirement, schema_capability)
            for gate in manifest["gates"]:
                validate_against_schema(gate, schema_gate)
            self.assertEqual(receipt["validation_status"], "PASS")
            self.assertEqual(receipt["packet_graph_id"], graph["record_id"])
            self.assertEqual(receipt["packet_graph_hash"], graph["graph_hash"])
            self.assertEqual(manifest["authority_effect"], "NONE")
            self.assertEqual(receipt["authority_effect"], "NONE")
        self.assertEqual(styles, ["DSAI", "C2P", "ESLI"])

    def test_materialisation_is_order_independent_and_round_trips(self) -> None:
        programme = self.fixture["programmes"][0]
        manifest_a, graph_a, receipt_a = self.materialise(programme)
        manifest_b, graph_b, receipt_b = materialise_programme(
            programme_id=programme["programme_id"],
            baseline_main="a" * 40,
            plan_source_ref=self.source_ref(programme),
            packets=list(reversed(programme["packets"])),
            gates=list(reversed(programme["gates"])),
            known_capability_ids=reversed(sorted(self.capability_ids)),
        )
        self.assertEqual(manifest_a["programme_manifest_id"], manifest_b["programme_manifest_id"])
        self.assertEqual(graph_a["graph_hash"], graph_b["graph_hash"])
        self.assertEqual(
            receipt_a["materialisation_receipt_id"],
            receipt_b["materialisation_receipt_id"],
        )
        self.assertEqual(json.loads(json.dumps(manifest_a)), manifest_a)
        self.assertEqual(json.loads(json.dumps(receipt_a)), receipt_a)

    def test_source_hash_and_post_materialisation_drift_fail_closed(self) -> None:
        source_content = b"ratified-plan-bytes"
        source_hash = hashlib.sha256(source_content).hexdigest()
        source_ref = build_plan_source_ref(
            plan_id="PLAN-X",
            plan_version="0.1",
            source_ref="plan-x.docx",
            source_sha256=source_hash,
        )
        verify_plan_source(source_ref, source_content)
        with self.assertRaisesRegex(PlanMaterialisationError, "source hash mismatch"):
            verify_plan_source(source_ref, b"changed-plan-bytes")

        programme = self.fixture["programmes"][0]
        _, _, receipt = self.materialise(programme)
        fixture_source = self.source_ref(programme)
        verify_materialisation_freshness(
            receipt=receipt,
            plan_source_ref=fixture_source,
            current_source_sha256=fixture_source["source_sha256"],
        )
        with self.assertRaisesRegex(
            PlanMaterialisationError, "governing plan source changed"
        ):
            verify_materialisation_freshness(
                receipt=receipt,
                plan_source_ref=fixture_source,
                current_source_sha256="f" * 64,
            )

    def test_missing_contract_duplicate_ids_and_unknown_references_fail_closed(self) -> None:
        programme = copy.deepcopy(self.fixture["programmes"][0])

        missing = copy.deepcopy(programme)
        del missing["packets"][0]["rollback"]
        with self.assertRaisesRegex(PlanMaterialisationError, "missing packet fields"):
            self.materialise(missing)

        duplicate = copy.deepcopy(programme)
        duplicate["packets"].append(copy.deepcopy(duplicate["packets"][0]))
        duplicate["packets"][-1]["next_packet"] = None
        with self.assertRaisesRegex(PlanMaterialisationError, "duplicate packet identity"):
            self.materialise(duplicate)

        unknown_gate = copy.deepcopy(programme)
        unknown_gate["packets"][0]["gate_ids"] = ["NOT-A-GATE"]
        with self.assertRaisesRegex(PlanMaterialisationError, "unknown gate references"):
            self.materialise(unknown_gate)

        unknown_prerequisite = copy.deepcopy(programme)
        unknown_prerequisite["packets"][1]["prerequisites"] = ["MISSING-WP"]
        with self.assertRaisesRegex(
            PlanMaterialisationError, "unknown internal prerequisites"
        ):
            self.materialise(unknown_prerequisite)

    def test_cycles_and_inconsistent_successors_fail_closed(self) -> None:
        programme = copy.deepcopy(self.fixture["programmes"][0])
        cyclic = copy.deepcopy(programme)
        cyclic["packets"][0]["prerequisites"] = ["DSAI-WP2"]
        cyclic["packets"][1]["prerequisites"] = ["DSAI-WP1"]
        with self.assertRaisesRegex(PlanMaterialisationError, "cycle detected"):
            self.materialise(cyclic)

        inconsistent = copy.deepcopy(programme)
        inconsistent["packets"][1]["prerequisites"] = []
        with self.assertRaisesRegex(PlanMaterialisationError, "inconsistent"):
            self.materialise(inconsistent)

    def test_reserved_authority_cannot_hide_under_auto_gate(self) -> None:
        programme = copy.deepcopy(self.fixture["programmes"][0])
        programme["packets"][0]["authority_delta"] = "SELECTOR_ACTIVATION"
        with self.assertRaisesRegex(PlanMaterialisationError, "reserved authority"):
            self.materialise(programme)

        gate_reserved = copy.deepcopy(self.fixture["programmes"][0])
        gate_reserved["gates"][0]["authority_delta"] = "VALIDATION_ACCESS"
        with self.assertRaisesRegex(PlanMaterialisationError, "cannot be auto-ratifiable"):
            self.materialise(gate_reserved)

    def test_unknown_mandatory_capability_blocks_but_unknown_optional_does_not_resolve(self) -> None:
        programme = copy.deepcopy(self.fixture["programmes"][0])
        programme["packets"][0]["capability_requirements"][0]["capability_id"] = "UNKNOWN-MANDATORY"
        with self.assertRaisesRegex(PlanMaterialisationError, "unknown mandatory capability"):
            self.materialise(programme)

        optional = copy.deepcopy(self.fixture["programmes"][0])
        optional["packets"][0]["capability_requirements"].append(
            {
                "capability_id": "UNKNOWN-OPTIONAL",
                "version_range": ">=0.1,<1.0",
                "required_tier": "QUALIFIED",
                "mandatory": False,
                "reason": "Optional future adapter; not execution-required.",
            }
        )
        _, graph, _ = self.materialise(optional)
        node = next(row for row in graph["nodes"] if row["packet_id"] == "DSAI-WP1")
        self.assertNotIn("UNKNOWN-OPTIONAL", node["required_capabilities"])

    def test_materialised_graph_is_consumable_by_existing_dsai_eligibility(self) -> None:
        programme = self.fixture["programmes"][0]
        _, graph, _ = self.materialise(programme)
        blocked = build_packet_eligibility_record(
            packet_id="DSAI-WP2",
            packet_graph=graph,
            completed_prerequisites=[],
        )
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["missing_prerequisites"], ["DSAI-WP1"])
        eligible = build_packet_eligibility_record(
            packet_id="DSAI-WP2",
            packet_graph=graph,
            completed_prerequisites=["DSAI-WP1"],
        )
        self.assertEqual(eligible["status"], "ELIGIBLE")

    def test_checked_in_ppm_materialisation_rebuilds_exactly(self) -> None:
        root = ROOT / "docs/implementation/plan-packet-materialisation-v0-1"
        transcription = load_json(root / "APPROVED_SCOPE_TRANSCRIPTION.json")
        source_text = (root / "GOVERNING_SCOPE.md").read_text(encoding="utf-8")
        source_ref = load_json(root / "PLAN_SOURCE_REF.json")
        self.assertEqual(
            source_ref,
            build_plan_source_ref(
                plan_id=transcription["plan_id"],
                plan_version=transcription["plan_version"],
                source_ref=transcription["source_ref"],
                source_sha256=transcription["source_sha256"],
            ),
        )
        verify_plan_source(source_ref, source_text)
        manifest, graph, receipt = materialise_programme(
            programme_id=transcription["programme_id"],
            baseline_main=transcription["baseline_main"],
            plan_source_ref=source_ref,
            packets=transcription["packets"],
            gates=transcription["gates"],
            known_capability_ids=self.capability_ids,
            source_content=source_text,
        )
        self.assertEqual(manifest, load_json(root / "PROGRAMME_MANIFEST.json"))
        self.assertEqual(graph, load_json(root / "PACKET_GRAPH_SNAPSHOT.json"))
        self.assertEqual(receipt, load_json(root / "MATERIALISATION_RECEIPT.json"))


if __name__ == "__main__":
    unittest.main()
