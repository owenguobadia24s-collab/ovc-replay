import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from ovc.programme_genesis import (
    AppendOnlyLedger,
    LedgerError,
    ProjectionError,
    build_partitioned_projection,
    canonical_event_bytes,
    compare_programme_state,
    event_digest,
    project_programme,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "registries/governance/programme_genesis"
FIXTURE_ROOT = ROOT / "fixtures/governance/programme_genesis"
CONTRACT = ROOT / "contracts/governance/programme_genesis/PORTFOLIO_LEDGER_AND_PROJECTION_CONTRACT_v0_1.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def event_registry() -> tuple[set[str], dict[str, int]]:
    registry = load_json(REGISTRY_ROOT / "EVENT_TYPE_REGISTRY_v0_1.json")
    allowed = {row["event_type"] for row in registry["event_types"]}
    precedence = {row["event_type"]: row["precedence"] for row in registry["event_types"]}
    return allowed, precedence


def class_partitions() -> dict[str, str]:
    registry = load_json(REGISTRY_ROOT / "PROGRAMME_CLASS_REGISTRY_v0_1.json")
    return {row["class_id"]: row["partition"] for row in registry["classes"]}


def make_event(event_id: str, event_type: str, first_valid_at: str, payload: dict | None = None) -> dict:
    return {
        "record_type": "PROGRAMME_EVENT",
        "schema_version": "0.1",
        "event_id": event_id,
        "programme_id": "OVC-PG-v0.2",
        "event_type": event_type,
        "observed_at": first_valid_at,
        "first_valid_at": first_valid_at,
        "actor_class": "REPOSITORY_EVENT",
        "source_refs": [
            {
                "source_type": "COMMIT",
                "identity": "e9938883d0346e305efee57bd6618da61d4cb844",
                "path": None,
                "hash": None,
                "precedence": 6,
                "authority_role": "SUPPORTING",
            }
        ],
        "authority_effect": "NONE",
        "payload": payload or {},
        "supersedes": None,
        "rollback": "Preserve the event and append a superseding correction.",
    }


class ProgrammeGenesisWP2Tests(unittest.TestCase):
    def test_canonical_event_identity_is_order_and_runtime_independent(self) -> None:
        event = make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00")
        reordered = dict(reversed(list(event.items())))
        payload = canonical_event_bytes(event)
        self.assertEqual(payload, canonical_event_bytes(reordered))
        self.assertEqual(event_digest(event), event_digest(reordered))
        self.assertNotIn(b'": ', payload)
        self.assertNotIn(b', "', payload)

    def test_append_only_ledger_preserves_existing_bytes_and_rejects_duplicates(self) -> None:
        allowed, _ = event_registry()
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "portfolio-events.jsonl"
            ledger = AppendOnlyLedger(ledger_path, allowed)
            first = make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00", {"packet_id": "PG-WP2", "gate_id": "PG-G2"})
            second = make_event("PGE.OVC-PG-v0.2.PACKET_IMPLEMENTED.001", "PACKET_IMPLEMENTED", "2026-08-03T18:05:00+01:00")
            first_digest = ledger.append(first)
            first_bytes = ledger_path.read_bytes()
            ledger.append(second)
            self.assertTrue(ledger_path.read_bytes().startswith(first_bytes))
            self.assertEqual([first, second], ledger.read_all())
            self.assertEqual(first_digest, ledger.inventory()["event_digests"][first["event_id"]])
            with self.assertRaisesRegex(LedgerError, "duplicate event_id"):
                ledger.append(first)

    def test_authority_effect_requires_authoritative_operator_decision(self) -> None:
        allowed, _ = event_registry()
        event = make_event("PGE.OVC-PG-v0.2.GATE_DECIDED.001", "GATE_DECIDED", "2026-08-03T18:10:00+01:00", {"decision": "PASS"})
        event["authority_effect"] = "GRANTED_BY_ACCEPTED_DECISION"
        event["actor_class"] = "DELEGATED_AUTOMATION"
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(LedgerError, "authoritative operator decision"):
                AppendOnlyLedger(Path(temp_dir) / "events.jsonl", allowed).append(event)
            event["source_refs"].append(
                {
                    "source_type": "OPERATOR_DECISION",
                    "identity": "PG-G0.OPERATOR.PASS.20260803T184400+0100",
                    "path": "docs/releases/programme-genesis-v0-2/pg-g0/PG_G0_OPERATOR_DECISION.json",
                    "hash": None,
                    "precedence": 1,
                    "authority_role": "AUTHORITATIVE",
                }
            )
            AppendOnlyLedger(Path(temp_dir) / "accepted.jsonl", allowed).append(event)

    def test_projection_order_is_first_valid_precedence_then_identity(self) -> None:
        _, precedence = event_registry()
        events = [
            make_event("PGE.OVC-PG-v0.2.GATE_READY.002", "GATE_READY", "2026-08-03T18:10:00+01:00", {"gate_id": "PG-G2"}),
            make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00", {"packet_id": "PG-WP2", "gate_id": "PG-G2"}),
            make_event("PGE.OVC-PG-v0.2.QA_REVIEWED.001", "QA_REVIEWED", "2026-08-03T18:10:00+01:00"),
            make_event("PGE.OVC-PG-v0.2.GATE_READY.001", "GATE_READY", "2026-08-03T18:10:00+01:00", {"gate_id": "PG-G2"}),
        ]
        projection = project_programme("OVC-PG-v0.2", reversed(events), precedence)
        self.assertEqual(
            [
                "PGE.OVC-PG-v0.2.PACKET_STARTED.001",
                "PGE.OVC-PG-v0.2.QA_REVIEWED.001",
                "PGE.OVC-PG-v0.2.GATE_READY.001",
                "PGE.OVC-PG-v0.2.GATE_READY.002",
            ],
            projection["event_order"],
        )
        self.assertEqual("GATE_READY", projection["status"])
        self.assertEqual("PG-WP2", projection["current_packet"])

    def test_partitioned_projection_is_deterministic_and_cross_partition_unique(self) -> None:
        _, precedence = event_registry()
        genesis = load_json(FIXTURE_ROOT / "valid_programme_genesis_v0_1.json")
        event = make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00", {"packet_id": "PG-WP2", "gate_id": "PG-G2"})
        first = build_partitioned_projection([genesis], [event], precedence, class_partitions())
        second = build_partitioned_projection(list(reversed([genesis])), list(reversed([event])), precedence, class_partitions())
        self.assertEqual(first, second)
        self.assertEqual(1, first["programme_count"])
        self.assertTrue(first["cross_partition_checks"]["unique_programme_identity"])
        duplicate = deepcopy(genesis)
        duplicate["genesis_id"] = "GENESIS.OVC-PG-v0.2.DUPLICATE"
        with self.assertRaisesRegex(ProjectionError, "programme identity"):
            build_partitioned_projection([genesis, duplicate], [event], precedence, class_partitions())

    def test_orphan_event_fails_closed(self) -> None:
        _, precedence = event_registry()
        genesis = load_json(FIXTURE_ROOT / "valid_programme_genesis_v0_1.json")
        event = make_event("PGE.ORPHAN.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00")
        event["programme_id"] = "OVC-ORPHAN-v0.1"
        with self.assertRaisesRegex(ProjectionError, "orphan programme events"):
            build_partitioned_projection([genesis], [event], precedence, class_partitions())

    def test_state_synchronisation_never_repairs_or_overwrites_source(self) -> None:
        source = {"programme_id": "OVC-PG-v0.2", "status": "QA_REVIEW", "current_packet": "PG-WP2", "current_gate": "PG-G2", "blockers": [], "next_action": "RUN_QA"}
        projection = {"programme_id": "OVC-PG-v0.2", "status": "RUNNING", "current_packet": "PG-WP2", "current_gate": "PG-G2", "blockers": [], "next_action": None}
        result = compare_programme_state(source, projection, source_commit="a" * 40, projection_source_commit="b" * 40)
        self.assertEqual(source, result["effective_state"])
        self.assertFalse(result["repair_performed"])
        self.assertFalse(result["enforcement_allowed"])
        self.assertEqual("CONFLICT", result["status"])
        finding_types = {finding["finding_type"] for finding in result["findings"]}
        self.assertTrue({"STALE_PROJECTION", "STATE_SOURCE_CONFLICT"}.issubset(finding_types))

    def test_ledger_contract_preserves_disabled_authority(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("append only", text)
        self.assertIn("programme-owned machine-readable state is the effective state", text)
        self.assertIn("enforcement remains disabled before `PG-G6`", text)
        self.assertIn("migration remains denied before `PG-G3A`", text)
        self.assertIn("Never rewrite the ledger or programme-owned state", text)


if __name__ == "__main__":
    unittest.main()
