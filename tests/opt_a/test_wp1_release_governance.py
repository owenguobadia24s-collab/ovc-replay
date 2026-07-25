from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "docs" / "releases" / "opt-a-v2" / "governance"
REGISTRIES = ROOT / "registries" / "releases"
SCHEMAS = ROOT / "schemas" / "opt_a"
HISTORICAL = (
    ROOT
    / "legacy"
    / "quarantine"
    / "abcd-engine-v1-c0ad7ba"
    / "docs"
    / "history"
    / "releases"
    / "opt-a-discovery-2026-h1"
)
BASELINE = "a9902c97e21131b1882b4c11ca3a2a79273e7c77"
RESET_HEAD = "71c7c5513efb9bb8d214d118be03090664050c21"
V1_ID = "OPT-A.GBPUSD.2026H1.v1"
V2_IDS = {
    "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
    "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
    "OPT-A.GBPUSD.VALIDATION.2025.v2",
}
EXPECTED_BLOBS = {
    "OPT_A_SEAL_MANIFEST.json": "56367dd59398ff8a64e12cdd48e60178fdb334ce",
    "OPT_A_SEAL_RECORD.md": "b16aadb0154f86b418b2653e3b33f468952813ae",
}


def git_blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", "--", path], cwd=ROOT, text=True
    ).strip()


class WP1ReleaseGovernanceTests(unittest.TestCase):
    def test_r0_merge_is_pinned_as_wp1_baseline(self) -> None:
        ratification = (
            ROOT
            / "docs"
            / "plans"
            / "opt_a_v2"
            / "OVC_OPT_A_V2_PROGRAMME_RATIFICATION_v0_2.md"
        ).read_text(encoding="utf-8")
        self.assertIn(BASELINE, ratification)
        self.assertIn(RESET_HEAD, ratification)
        self.assertIn("e0e9b0f545b3d5b147000ff69bf501b57874f2e8ee4aba84c4f6c4475cb9e0f6", ratification)

    def test_historical_v1_files_are_hash_locked_and_unchanged(self) -> None:
        for filename, expected in EXPECTED_BLOBS.items():
            path = HISTORICAL / filename
            self.assertTrue(path.is_file(), filename)
            self.assertEqual(expected, git_blob(path), filename)

    def test_historical_manifest_identity_and_inventory_are_unchanged(self) -> None:
        manifest = json.loads((HISTORICAL / "OPT_A_SEAL_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(V1_ID, manifest["seal_id"])
        self.assertEqual("SEALED_RESEARCH_AUTHORITY", manifest["status"])
        self.assertEqual("0927f7a2b078d670370eb9ec26718f3e2ff0d97708df1f785a9333264415ef99", manifest["seal_hash"])
        self.assertEqual(14, len(manifest["artifacts"]))
        self.assertEqual(13_906_357, sum(item["size_bytes"] for item in manifest["artifacts"]))

    def test_v1_supersession_record_has_required_disposition(self) -> None:
        record = json.loads((GOVERNANCE / "OPT_A_V1_SUPERSESSION_RECORD.json").read_text(encoding="utf-8"))
        expected = {
            "release_id": V1_ID,
            "current_authority_state": "SUPERSEDED",
            "disposition": "SUPERSEDED_UNPUBLISHED",
            "availability_state": "MISSING",
            "publication_status": "NEVER_PUBLISHED",
            "reproducibility_status": "NOT_REPRODUCIBLE_MISSING_PAYLOAD",
            "r2_canonical_status": "ABSENT",
            "active_selector": False,
            "selector_state": "NONE",
            "reason": "EXACT_SEALED_PAYLOAD_UNAVAILABLE",
            "replacement_policy": "NEW_BYTES_REQUIRE_NEW_RELEASE_ID",
        }
        for key, value in expected.items():
            self.assertEqual(value, record[key], key)
        for prohibited in (
            "NEW_REPLAY_INPUT",
            "CANONICAL_PUBLICATION",
            "SELECTOR_FALLBACK",
            "ROLLBACK_TARGET",
            "UNTOUCHED_VALIDATION",
        ):
            self.assertIn(prohibited, record["prohibited_use"])

    def test_release_state_schema_defines_orthogonal_dimensions(self) -> None:
        schema = json.loads((SCHEMAS / "opt_a_release_state_v0_2.json").read_text(encoding="utf-8"))
        required = set(schema["required"])
        dimensions = {
            "lifecycle_state",
            "authority_state",
            "qa_state",
            "availability_state",
            "publication_status",
            "consumption_state",
            "selector_state",
            "active_selector",
        }
        self.assertTrue(dimensions <= required)
        self.assertIn("SUPERSEDED", schema["properties"]["authority_state"]["enum"])
        self.assertIn("LOCKED_UNCONSUMED", schema["properties"]["consumption_state"]["enum"])
        self.assertIn("ABANDONED_BY_POLICY", schema["properties"]["publication_status"]["enum"])

    def test_registry_schema_pins_programme_and_role_set(self) -> None:
        schema = json.loads((SCHEMAS / "opt_a_release_registry_v0_1.json").read_text(encoding="utf-8"))
        properties = schema["properties"]
        self.assertEqual("OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2", properties["programme_id"]["const"])
        self.assertEqual("OPT-A.GBPUSD.ROLESET.2021_2025.v1", properties["release_set_id"]["const"])
        self.assertEqual(4, properties["releases"]["minItems"])
        self.assertEqual(4, properties["releases"]["maxItems"])

    def test_release_registry_separates_v1_from_exact_v2_identities(self) -> None:
        registry = (REGISTRIES / "OPT_A_RELEASE_REGISTRY.yaml").read_text(encoding="utf-8")
        self.assertEqual(1, registry.count(f"release_id: {V1_ID}"))
        for release_id in V2_IDS:
            self.assertEqual(1, registry.count(f"release_id: {release_id}"), release_id)
            self.assertNotEqual(V1_ID, release_id)
        self.assertIn("disposition", (GOVERNANCE / "OPT_A_V1_SUPERSESSION_RECORD.json").read_text(encoding="utf-8"))
        self.assertIn("NEW_BYTES_REQUIRE_NEW_RELEASE_ID", registry)

    def test_all_role_selectors_remain_none_and_v1_cannot_return(self) -> None:
        selectors = (REGISTRIES / "OPT_A_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("state: NONE", selectors)
        self.assertEqual(3, selectors.count("selector_state: NONE"))
        self.assertIn("all_role_selectors: NONE", selectors)
        self.assertIn("historical_v1_reactivation: PROHIBITED", selectors)
        self.assertNotIn(V1_ID, selectors)

    def test_validation_access_is_default_deny(self) -> None:
        access = (REGISTRIES / "OPT_A_VALIDATION_ACCESS_REGISTRY.yaml").read_text(encoding="utf-8")
        self.assertIn("consumption_state: LOCKED_UNCONSUMED", access)
        self.assertIn("default_access: DENIED", access)
        self.assertIn("active_approval_id: null", access)
        self.assertIn("approvals: []", access)

    def test_wp1_does_not_grant_market_or_publication_authority(self) -> None:
        authority = (ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        self.assertGreaterEqual(authority.count(": NONE"), 8)
        self.assertIn("market_authority: false", authority)
        selectors = (REGISTRIES / "OPT_A_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("market_authority: NONE", selectors)
        self.assertNotIn("selector_state: ACTIVE", selectors)

    def test_external_artifact_contract_preserves_git_boundary(self) -> None:
        contract = (ROOT / "contracts" / "opt_a" / "OVC_EXTERNAL_ARTIFACT_ROOT_CONTRACT_v0_1.md").read_text(encoding="utf-8")
        self.assertIn("OVC_EXTERNAL_ARTIFACT_ROOT", contract)
        self.assertIn("must not persist the resolved absolute path", contract)
        self.assertIn("Raw provider payloads", contract)
        self.assertIn("may not enter Git", contract)

    def test_recovery_audit_does_not_overclaim_current_external_state(self) -> None:
        audit = (GOVERNANCE / "OPT_A_V1_RECOVERY_AUDIT.md").read_text(encoding="utf-8")
        self.assertIn("NO_EXACT_PAYLOAD_MATCH_RECORDED", audit)
        self.assertIn("NOT_EVALUATED_BY_GITHUB_RUNNER", audit)
        self.assertIn("UNAVAILABLE_FOR_REPRODUCTION", audit)


if __name__ == "__main__":
    unittest.main()
