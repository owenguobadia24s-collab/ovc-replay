from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/programme-genesis-native-portfolio-v0-2"
R1 = BASE / "pgn-g3-r1/PGN_G3_R1_ARTIFACT_GOVERNANCE_SUPPLEMENT.json"
R2 = BASE / "pgn-g3-r2/PGN_G3_R2_ARTIFACT_GOVERNANCE_SUPPLEMENT.json"
R3 = BASE / "pgn-g3-r3/PGN_G3_R3_ARTIFACT_GOVERNANCE_CROSSWALK.json"
R4 = BASE / "pgn-g3-r4/PGN_G3_R4_ARTIFACT_GOVERNANCE_CROSSWALK.json"
PROTOCOL = BASE / "pgn-g3-r3/PGN_G3_REVIEW_PROTOCOL_AMENDMENT_v0_1.json"
DECISION = BASE / "pgn-g3-r3/PGN_G3_R3_ADJUST_SCOPE_OPERATOR_DECISION.json"
SCHEMA = ROOT / "schemas/governance/programme_genesis/pgn_artifact_governance_crosswalk_v0_1.schema.json"
CONTRACT = ROOT / "contracts/governance/programme_genesis/OVC_PGN_ARTIFACT_GOVERNANCE_CROSSWALK_CONTRACT_v0_1.md"
VALID = ROOT / "fixtures/governance/programme_genesis/valid_pgn_artifact_governance_crosswalk_v0_1.json"
INVALID = ROOT / "fixtures/governance/programme_genesis/invalid_pgn_artifact_governance_crosswalk_authority_leak_v0_1.json"
R1_RECEIPT = BASE / "pgn-g3/reviews/PGN_G3_R1_ACKNOWLEDGEMENT_RECEIPT.json"
R2_RECEIPT = BASE / "pgn-g3/reviews/PGN_G3_R2_ACKNOWLEDGEMENT_RECEIPT.json"
R3_RECEIPT = BASE / "pgn-g3/reviews/PGN_G3_R3_ACKNOWLEDGEMENT_RECEIPT.json"

ALLOWED_EVIDENCE = {
    "SOURCE_EXPLICIT",
    "LINEAGE_EXPLICIT",
    "PATH_AND_CONTENT_CORROBORATED",
    "CANDIDATE_RELATION",
    "UNRESOLVED",
}
ALLOWED_RELATIONSHIPS = {
    "EVIDENCE_ROOT_OF",
    "PLAN_GOVERNED_BY",
    "RELEASE_PRODUCED_BY",
    "GATE_PACKET_OF",
    "DECISION_RECORD_OF",
    "HISTORICAL_EVIDENCE_OF",
    "LINEAGE_RECORD_OF",
    "REFERENCES",
    "CONSUMES",
    "UNRESOLVED_RELATION",
}
HASH = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


def assert_authority_neutral(test: unittest.TestCase, value: dict) -> None:
    test.assertEqual("NONE", value["authority_effect"])
    test.assertEqual(value["candidate_count"], len(value["candidates"]))
    test.assertLessEqual(value["candidate_count"], 3)
    for candidate in value["candidates"]:
        test.assertEqual("CANDIDATE_UNAPPROVED", candidate["candidate_status"])
        test.assertEqual("MATERIALISED_UNAPPROVED", candidate["crosswalk_status"])
        test.assertEqual("NONE", candidate["authority_effect"])
        test.assertTrue(candidate["relationships"])
        for relationship in candidate["relationships"]:
            test.assertEqual(candidate["programme_id"], relationship["governing_programme_id"])
            test.assertIn(relationship["relationship_type"], ALLOWED_RELATIONSHIPS)
            test.assertIn(relationship["evidence_status"], ALLOWED_EVIDENCE)
            test.assertEqual("NONE", relationship["authority_effect"])
            test.assertTrue(relationship["evidence_sources"])
            for source in relationship["evidence_sources"]:
                test.assertTrue(source["path"])
                test.assertRegex(source["hash"], HASH)
                test.assertIn(source["hash_kind"], {"GIT_BLOB_SHA", "SHA256", "SOURCE_SET_SHA256", "COMMIT_SHA"})


class PgnG3ArtifactGovernanceCrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.r1 = load(R1)
        cls.r2 = load(R2)
        cls.r3 = load(R3)
        cls.r4 = load(R4)
        cls.protocol = load(PROTOCOL)
        cls.decision = load(DECISION)
        cls.r3_receipt = load(R3_RECEIPT)
        cls.schema = load(SCHEMA)
        cls.valid = load(VALID)
        cls.invalid = load(INVALID)

    def test_contract_schema_and_negative_fixture(self) -> None:
        self.assertTrue(CONTRACT.exists())
        self.assertEqual("NONE", self.schema["properties"]["authority_effect"]["const"])
        evidence_enum = set(self.schema["$defs"]["relationship"]["properties"]["evidence_status"]["enum"])
        self.assertEqual(ALLOWED_EVIDENCE, evidence_enum)
        assert_authority_neutral(self, self.valid)
        with self.assertRaises(AssertionError):
            assert_authority_neutral(self, self.invalid)

    def test_operator_adjust_scope_decision_is_exact_and_non_authorising(self) -> None:
        self.assertEqual("PGN-G3-R3.OPERATOR.ADJUST_SCOPE.20260805T152000+0100", self.decision["decision_id"])
        self.assertEqual("ADJUST_SCOPE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("NONE", self.decision["authority_effect"])
        self.assertTrue(self.decision["scope_delta"]["preserve_existing_acknowledgements"])
        self.assertFalse(self.decision["scope_delta"]["existing_acknowledgements_are_adoption"])
        self.assertIn("NATIVE_ADOPTION", self.decision["denied"])
        self.assertIn("CROSS_PROGRAMME_HARD_DEPENDENCY_ACCEPTANCE", self.decision["denied"])

    def test_protocol_applies_to_all_six_groups_and_receipt_unlocks_only_r4(self) -> None:
        expected = [f"PGN-G3-R{i}" for i in range(1, 7)]
        self.assertEqual(expected, self.protocol["applies_to"])
        self.assertEqual("PGN_G3_R3_AMENDED_ACKNOWLEDGEMENT_RECEIPT_MERGED", self.protocol["r4_unlock_condition"])
        self.assertEqual("DENIED_PENDING_PGN_G5", self.protocol["cross_programme_edge_acceptance"])
        self.assertEqual("NONE", self.protocol["authority_effect"])
        self.assertTrue(R1_RECEIPT.exists())
        self.assertTrue(R2_RECEIPT.exists())
        self.assertTrue(R3_RECEIPT.exists())
        self.assertEqual("DISCLOSE_AND_MATERIALISE_PGN_G3_R4_ONLY", self.r3_receipt["authority_effect"])
        self.assertEqual("NONE", self.r3_receipt["native_adoption"])
        self.assertEqual("LOCKED", self.r3_receipt["later_groups_beyond_r4"])

    def test_materialised_crosswalks_are_complete_and_authority_neutral(self) -> None:
        self.assertEqual("RETROSPECTIVE_SUPPLEMENT_MATERIALISED_UNAPPROVED", self.r1["status"])
        self.assertEqual("RETROSPECTIVE_SUPPLEMENT_MATERIALISED_UNAPPROVED", self.r2["status"])
        self.assertEqual("MATERIALISED_UNAPPROVED", self.r3["status"])
        self.assertEqual("MATERIALISED_UNAPPROVED", self.r4["status"])
        for value in (self.r1, self.r2, self.r3, self.r4):
            assert_authority_neutral(self, value)

        ids = [candidate["programme_id"] for value in (self.r1, self.r2, self.r3, self.r4) for candidate in value["candidates"]]
        self.assertEqual(12, len(ids))
        self.assertEqual(12, len(set(ids)))
        self.assertIn("OVC-DEV-ACCEL-v0.2", ids)
        self.assertIn("OVC-RESEARCH-CONSOLE.v0.3", ids)
        self.assertIn("OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1", ids)

    def test_candidate_relations_remain_visible_and_non_authoritative(self) -> None:
        r3_candidates = [
            relationship
            for candidate in self.r3["candidates"]
            for relationship in candidate["relationships"]
            if relationship["evidence_status"] == "CANDIDATE_RELATION"
        ]
        r4_candidates = [
            relationship
            for candidate in self.r4["candidates"]
            for relationship in candidate["relationships"]
            if relationship["evidence_status"] == "CANDIDATE_RELATION"
        ]
        self.assertEqual(2, len(r3_candidates))
        self.assertEqual(1, len(r4_candidates))
        self.assertEqual("OVC-RESEARCH-CONSOLE-V0.2-IMPLEMENTATION-PLAN-0.1", r4_candidates[0]["artifact_id"])
        self.assertTrue(all(item["ambiguity_or_competing_owner"] for item in r3_candidates + r4_candidates))
        self.assertTrue(all(item["authority_effect"] == "NONE" for item in r3_candidates + r4_candidates))

    def test_r4_supersession_lineage_preserves_no_authority_transfer(self) -> None:
        lineage = [
            relationship
            for candidate in self.r4["candidates"]
            for relationship in candidate["relationships"]
            if relationship["evidence_status"] == "LINEAGE_EXPLICIT"
        ]
        self.assertEqual(2, len(lineage))
        self.assertTrue(all(item["relationship_type"] == "LINEAGE_RECORD_OF" for item in lineage))
        self.assertTrue(all(item["authority_effect"] == "NONE" for item in lineage))
        self.assertTrue(all(item["ambiguity_or_competing_owner"] for item in lineage))

    def test_opt_a_lineage_and_validation_lock_are_preserved(self) -> None:
        opt_a = next(candidate for candidate in self.r2["candidates"] if candidate["programme_id"] == "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2")
        relations = {item["artifact_id"]: item for item in opt_a["relationships"]}
        self.assertEqual("LINEAGE_EXPLICIT", relations["OPT-A.GBPUSD.2026H1.v1"]["evidence_status"])
        self.assertEqual("RELEASE_PRODUCED_BY", relations["OPT-A.GBPUSD.VALIDATION.2025.v2"]["relationship_type"])
        self.assertIn("locked and unconsumed", relations["OPT-A.GBPUSD.VALIDATION.2025.v2"]["ambiguity_or_competing_owner"])


if __name__ == "__main__":
    unittest.main()
