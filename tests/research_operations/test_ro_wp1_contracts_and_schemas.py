from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ROWP1ContractsAndSchemasTests(unittest.TestCase):
    def test_required_outputs_exist(self) -> None:
        required = (
            "contracts/research_operations/RESEARCH_OPERATIONS_AUTHORITY_BOUNDARY_v0_1.md",
            "contracts/research_operations/EVIDENCE_ENVELOPE_AND_IDENTITY_CONTRACT_v0_1.md",
            "contracts/research_operations/RESEARCH_RECORD_LIFECYCLE_POLICY_v0_1.md",
            "contracts/research_operations/ADMISSIBLE_CUTOFF_AND_VALIDATION_ISOLATION_POLICY_v0_1.md",
            "schemas/research_operations/research_records_v0_1.schema.json",
            "registries/research_operations/RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml",
            "registries/research_operations/RESEARCH_RECORD_TYPE_REGISTRY_v0_1.yaml",
            "registries/research_operations/RESEARCH_RECORD_LIFECYCLE_REGISTRY_v0_1.yaml",
            "src/ovc/research_operations/__init__.py",
            "fixtures/research_operations/ro_wp1/FIXTURE_PACK.json",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_schema_bundle_defines_ten_record_types(self) -> None:
        schema = json.loads((ROOT / "schemas/research_operations/research_records_v0_1.schema.json").read_text())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        expected = {"DataReleaseRef", "ResearchSession", "ObservationSnapshot", "ClaimRecord", "RealizationSnapshot", "EvidenceItem", "CaseBundle", "IncidentRecord", "DecisionRecord", "AuditEvent"}
        self.assertTrue(expected <= set(schema["$defs"]))
        self.assertNotIn("model_refs", schema["$defs"]["Envelope"]["required"])

    def test_fixture_pack_is_non_authoritative(self) -> None:
        pack = json.loads((ROOT / "fixtures/research_operations/ro_wp1/FIXTURE_PACK.json").read_text())
        self.assertEqual(pack["status"], "SYNTHETIC_NON_AUTHORITATIVE")
        self.assertEqual(pack["market_authority"], "NONE")
        self.assertGreaterEqual(len(pack["fixtures"]), 7)

    def test_wp1_invariants_remain_after_ro_g1_and_wp2_progression(self) -> None:
        authority = (ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml").read_text()
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)
        self.assertIn("ro_g1: PASS", authority)
        self.assertIn("ro_wp2: IMPLEMENTED_READY_FOR_RO_G2_REVIEW", authority)
        self.assertIn("active_research: NONE", authority)
        for token in ("market_authority: NONE", "probability_authority: NONE", "exposure_authority: NONE", "execution_authority: NONE", "agent_authority: NONE"):
            self.assertIn(token, authority)


if __name__ == "__main__":
    unittest.main()
