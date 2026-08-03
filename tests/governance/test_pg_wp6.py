import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.programme_genesis import (
    UpkeepError,
    build_candidate_event,
    load_upkeep_registry,
    persist_candidate_event,
    preview_candidate_events,
    validate_candidate_event,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "registries/governance/programme_genesis/UPKEEP_CANDIDATE_EVENT_REGISTRY_v0_1.json"
SCHEMA_PATH = ROOT / "schemas/governance/programme_genesis/upkeep_candidate_event_v0_1.schema.json"
CONTRACT_PATH = ROOT / "contracts/governance/programme_genesis/BOUNDED_UPKEEP_CANDIDATE_EVENT_CONTRACT_v0_1.md"
PROGRAMME_IDS = {"OVC-PG-v0.2", "OVC-MTA-v0.2"}
TARGET_BRANCH = "upkeep/pg-candidate-events/2026-08-03-health"
SOURCE_SHA = "a" * 64


def registry() -> dict:
    return load_upkeep_registry(REGISTRY_PATH)


def finding(identity: str = "finding-001", programme_id: str = "OVC-MTA-v0.2") -> dict:
    return {
        "programme_id": programme_id,
        "event_type": "HEALTH_FINDING_CANDIDATE",
        "source_kind": "PROGRAMME_HEALTH_FINDING",
        "source_finding_id": identity,
        "source_ref": {
            "path": "docs/releases/example/health.json",
            "sha256": SOURCE_SHA,
        },
        "observed_at": "2026-08-03T19:00:00+00:00",
        "first_valid_at": "2026-08-03T19:00:00+00:00",
        "proposed_payload": {
            "finding_type": "STALE_PROJECTION",
            "severity": "WARN",
            "message": "Projection should be reviewed against programme-owned state.",
        },
    }


def candidate(item: dict | None = None, *, active_registry: dict | None = None) -> dict:
    item = deepcopy(item or finding())
    active_registry = active_registry or registry()
    return build_candidate_event(
        programme_id=item["programme_id"],
        event_type=item["event_type"],
        source_kind=item["source_kind"],
        source_finding_id=item["source_finding_id"],
        source_path=item["source_ref"]["path"],
        source_sha256=item["source_ref"]["sha256"],
        observed_at=item["observed_at"],
        first_valid_at=item["first_valid_at"],
        proposed_payload=item["proposed_payload"],
        target_branch=TARGET_BRANCH,
        registry=active_registry,
        existing_programme_ids=PROGRAMME_IDS,
    )


class ProgrammeGenesisWP6Tests(unittest.TestCase):
    def test_registry_is_frozen_disabled_pending_pg_g7(self) -> None:
        value = registry()
        self.assertEqual("FROZEN_DISABLED_PENDING_PG_G7", value["status"])
        self.assertFalse(value["enabled"])
        self.assertTrue(value["preview_enabled"])
        self.assertEqual("PG-G7", value["activation_gate"])
        self.assertIsNone(value["activation_decision_id"])
        self.assertFalse(value["capabilities"]["candidate_persistence"])
        self.assertFalse(value["capabilities"]["programme_creation"])
        self.assertFalse(value["capabilities"]["programme_event_acceptance"])
        self.assertFalse(value["capabilities"]["approval"])
        self.assertFalse(value["capabilities"]["merge"])
        self.assertFalse(value["capabilities"]["main_write"])
        self.assertFalse(value["capabilities"]["publication"])
        self.assertEqual("NONE", value["authority_effect"])
        self.assertIn("AUTOMATIC_UPKEEP_BEFORE_PG_G7", value["reserved_authority_denials"])

    def test_candidate_identity_and_preview_are_deterministic(self) -> None:
        first = candidate()
        second = candidate()
        self.assertEqual(first, second)
        self.assertRegex(first["candidate_event_id"], r"^PG-UPKEEP-[0-9a-f]{24}$")
        self.assertEqual("CANDIDATE_UNAPPROVED", first["status"])
        self.assertEqual("NONE", first["authority_effect"])
        batch_a = preview_candidate_events(
            [finding("finding-002"), finding("finding-001")],
            registry=registry(),
            existing_programme_ids=PROGRAMME_IDS,
            target_branch=TARGET_BRANCH,
        )
        batch_b = preview_candidate_events(
            [finding("finding-001"), finding("finding-002")],
            registry=registry(),
            existing_programme_ids=PROGRAMME_IDS,
            target_branch=TARGET_BRANCH,
        )
        self.assertEqual(batch_a, batch_b)
        self.assertEqual(["finding-001", "finding-002"], [item["source_finding_id"] for item in batch_a])

    def test_unknown_programme_event_kind_and_source_kind_fail_closed(self) -> None:
        unknown = finding(programme_id="OVC-UNKNOWN-v1")
        with self.assertRaisesRegex(UpkeepError, "existing programme"):
            candidate(unknown)
        invalid_event = finding()
        invalid_event["event_type"] = "PROGRAMME_APPROVAL"
        with self.assertRaisesRegex(UpkeepError, "event type"):
            candidate(invalid_event)
        invalid_source = finding()
        invalid_source["source_kind"] = "CHAT_INFERENCE"
        with self.assertRaisesRegex(UpkeepError, "source kind"):
            candidate(invalid_source)

    def test_source_identity_and_first_valid_time_fail_closed(self) -> None:
        invalid_sha = finding()
        invalid_sha["source_ref"]["sha256"] = "ABC"
        with self.assertRaisesRegex(UpkeepError, "SHA-256"):
            candidate(invalid_sha)
        traversal = finding()
        traversal["source_ref"]["path"] = "../outside.json"
        with self.assertRaisesRegex(UpkeepError, "repository-relative"):
            candidate(traversal)
        naive_time = finding()
        naive_time["observed_at"] = "2026-08-03T19:00:00"
        with self.assertRaisesRegex(UpkeepError, "explicit timezone"):
            candidate(naive_time)
        early = finding()
        early["first_valid_at"] = "2026-08-03T18:59:59+00:00"
        with self.assertRaisesRegex(UpkeepError, "cannot precede"):
            candidate(early)

    def test_nested_authority_payloads_are_rejected(self) -> None:
        invalid = finding()
        invalid["proposed_payload"] = {
            "observation": "review needed",
            "nested": {"approved": True},
        }
        with self.assertRaisesRegex(UpkeepError, "forbidden authority fields"):
            candidate(invalid)
        invalid_list = finding()
        invalid_list["proposed_payload"] = {"items": [{"risk": 0.1}]}
        with self.assertRaisesRegex(UpkeepError, "forbidden authority fields"):
            candidate(invalid_list)

    def test_candidate_status_authority_and_identity_cannot_be_mutated(self) -> None:
        valid = candidate()
        wrong_status = deepcopy(valid)
        wrong_status["status"] = "APPROVED"
        with self.assertRaisesRegex(UpkeepError, "CANDIDATE_UNAPPROVED"):
            validate_candidate_event(wrong_status, registry(), existing_programme_ids=PROGRAMME_IDS)
        wrong_authority = deepcopy(valid)
        wrong_authority["authority_effect"] = "GRANTED"
        with self.assertRaisesRegex(UpkeepError, "authority_effect"):
            validate_candidate_event(wrong_authority, registry(), existing_programme_ids=PROGRAMME_IDS)
        changed_payload = deepcopy(valid)
        changed_payload["proposed_payload"]["severity"] = "BLOCK"
        with self.assertRaisesRegex(UpkeepError, "candidate_event_id"):
            validate_candidate_event(changed_payload, registry(), existing_programme_ids=PROGRAMME_IDS)

    def test_wrong_or_main_branch_is_rejected(self) -> None:
        item = candidate()
        item["target_branch"] = "main"
        with self.assertRaisesRegex(UpkeepError, "dedicated upkeep prefix"):
            validate_candidate_event(item, registry(), existing_programme_ids=PROGRAMME_IDS)
        item = candidate()
        item["target_branch"] = "feature/general"
        with self.assertRaisesRegex(UpkeepError, "dedicated upkeep prefix"):
            validate_candidate_event(item, registry(), existing_programme_ids=PROGRAMME_IDS)

    def test_preview_is_bounded_and_creates_no_files(self) -> None:
        value = registry()
        value["max_events_per_run"] = 1
        with self.assertRaisesRegex(UpkeepError, "max_events_per_run"):
            preview_candidate_events(
                [finding("finding-001"), finding("finding-002")],
                registry=value,
                existing_programme_ids=PROGRAMME_IDS,
                target_branch=TARGET_BRANCH,
            )
        with self.assertRaisesRegex(UpkeepError, "duplicate candidate identities"):
            preview_candidate_events(
                [finding("same"), finding("same")],
                registry=registry(),
                existing_programme_ids=PROGRAMME_IDS,
                target_branch=TARGET_BRANCH,
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preview_candidate_events(
                [finding()],
                registry=registry(),
                existing_programme_ids=PROGRAMME_IDS,
                target_branch=TARGET_BRANCH,
            )
            self.assertEqual([], list(root.rglob("*")))

    def test_persistence_is_denied_before_pg_g7_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaisesRegex(UpkeepError, "disabled pending PG-G7"):
                persist_candidate_event(
                    root,
                    candidate(),
                    registry=registry(),
                    branch_name=TARGET_BRANCH,
                    existing_programme_ids=PROGRAMME_IDS,
                )
            self.assertEqual([], list(root.rglob("*")))

    def test_synthetic_future_activation_is_dedicated_and_append_only(self) -> None:
        active = registry()
        active["enabled"] = True
        active["activation_decision_id"] = "PG-G7.OPERATOR.PASS.TEST_ONLY"
        active["capabilities"]["candidate_persistence"] = True
        item = candidate(active_registry=active)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            destination = persist_candidate_event(
                root,
                item,
                registry=active,
                branch_name=TARGET_BRANCH,
                existing_programme_ids=PROGRAMME_IDS,
            )
            self.assertTrue(destination.is_file())
            stored = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(item, stored)
            with self.assertRaisesRegex(UpkeepError, "already exists"):
                persist_candidate_event(
                    root,
                    item,
                    registry=active,
                    branch_name=TARGET_BRANCH,
                    existing_programme_ids=PROGRAMME_IDS,
                )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(UpkeepError, "dedicated candidate branch"):
                persist_candidate_event(
                    temp_dir,
                    item,
                    registry=active,
                    branch_name="feature/not-upkeep",
                    existing_programme_ids=PROGRAMME_IDS,
                )

    def test_schema_and_contract_preserve_human_governance(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual("CANDIDATE_UNAPPROVED", schema["properties"]["status"]["const"])
        self.assertEqual("NONE", schema["properties"]["authority_effect"]["const"])
        self.assertIn("upkeep/pg-candidate-events", schema["properties"]["target_branch"]["pattern"])
        contract = CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn("It does not activate automatic upkeep", contract)
        self.assertIn("cannot create or admit a programme", contract)
        self.assertIn("persistence is denied", contract)
        self.assertIn("may not create programmes, approve candidates, merge pull requests or write `main`", contract)
        self.assertIn("Code availability, passing tests and a merged disabled implementation do not grant upkeep authority", contract)


if __name__ == "__main__":
    unittest.main()
