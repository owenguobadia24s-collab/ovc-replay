import json
from copy import deepcopy
from pathlib import Path

import pytest

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


def test_canonical_event_identity_is_order_and_runtime_independent() -> None:
    event = make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00")
    reordered = dict(reversed(list(event.items())))
    assert canonical_event_bytes(event) == canonical_event_bytes(reordered)
    assert event_digest(event) == event_digest(reordered)
    assert b" " not in canonical_event_bytes(event)


def test_append_only_ledger_preserves_existing_bytes_and_rejects_duplicates(tmp_path: Path) -> None:
    allowed, _ = event_registry()
    ledger_path = tmp_path / "portfolio-events.jsonl"
    ledger = AppendOnlyLedger(ledger_path, allowed)
    first = make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00", {"packet_id": "PG-WP2", "gate_id": "PG-G2"})
    second = make_event("PGE.OVC-PG-v0.2.PACKET_IMPLEMENTED.001", "PACKET_IMPLEMENTED", "2026-08-03T18:05:00+01:00")

    first_digest = ledger.append(first)
    first_bytes = ledger_path.read_bytes()
    ledger.append(second)
    assert ledger_path.read_bytes().startswith(first_bytes)
    assert ledger.read_all() == [first, second]
    assert ledger.inventory()["event_digests"][first["event_id"]] == first_digest
    with pytest.raises(LedgerError, match="duplicate event_id"):
        ledger.append(first)


def test_authority_effect_requires_authoritative_operator_decision(tmp_path: Path) -> None:
    allowed, _ = event_registry()
    event = make_event("PGE.OVC-PG-v0.2.GATE_DECIDED.001", "GATE_DECIDED", "2026-08-03T18:10:00+01:00", {"decision": "PASS"})
    event["authority_effect"] = "GRANTED_BY_ACCEPTED_DECISION"
    event["actor_class"] = "DELEGATED_AUTOMATION"
    with pytest.raises(LedgerError, match="authoritative operator decision"):
        AppendOnlyLedger(tmp_path / "events.jsonl", allowed).append(event)

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
    AppendOnlyLedger(tmp_path / "accepted.jsonl", allowed).append(event)


def test_projection_order_is_first_valid_precedence_then_identity() -> None:
    _, precedence = event_registry()
    events = [
        make_event("PGE.OVC-PG-v0.2.GATE_READY.002", "GATE_READY", "2026-08-03T18:10:00+01:00", {"gate_id": "PG-G2"}),
        make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00", {"packet_id": "PG-WP2", "gate_id": "PG-G2"}),
        make_event("PGE.OVC-PG-v0.2.QA_REVIEWED.001", "QA_REVIEWED", "2026-08-03T18:10:00+01:00"),
        make_event("PGE.OVC-PG-v0.2.GATE_READY.001", "GATE_READY", "2026-08-03T18:10:00+01:00", {"gate_id": "PG-G2"}),
    ]
    projection = project_programme("OVC-PG-v0.2", reversed(events), precedence)
    assert projection["event_order"] == [
        "PGE.OVC-PG-v0.2.PACKET_STARTED.001",
        "PGE.OVC-PG-v0.2.QA_REVIEWED.001",
        "PGE.OVC-PG-v0.2.GATE_READY.001",
        "PGE.OVC-PG-v0.2.GATE_READY.002",
    ]
    assert projection["status"] == "GATE_READY"
    assert projection["current_packet"] == "PG-WP2"


def test_partitioned_projection_is_deterministic_and_cross_partition_unique() -> None:
    _, precedence = event_registry()
    genesis = load_json(FIXTURE_ROOT / "valid_programme_genesis_v0_1.json")
    event = make_event("PGE.OVC-PG-v0.2.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00", {"packet_id": "PG-WP2", "gate_id": "PG-G2"})
    first = build_partitioned_projection([genesis], [event], precedence, class_partitions())
    second = build_partitioned_projection(list(reversed([genesis])), list(reversed([event])), precedence, class_partitions())
    assert first == second
    assert first["programme_count"] == 1
    assert first["cross_partition_checks"]["unique_programme_identity"] is True

    duplicate = deepcopy(genesis)
    duplicate["genesis_id"] = "GENESIS.OVC-PG-v0.2.DUPLICATE"
    with pytest.raises(ProjectionError, match="programme identity"):
        build_partitioned_projection([genesis, duplicate], [event], precedence, class_partitions())


def test_orphan_event_fails_closed() -> None:
    _, precedence = event_registry()
    genesis = load_json(FIXTURE_ROOT / "valid_programme_genesis_v0_1.json")
    event = make_event("PGE.ORPHAN.PACKET_STARTED.001", "PACKET_STARTED", "2026-08-03T18:00:00+01:00")
    event["programme_id"] = "OVC-ORPHAN-v0.1"
    with pytest.raises(ProjectionError, match="orphan programme events"):
        build_partitioned_projection([genesis], [event], precedence, class_partitions())


def test_state_synchronisation_never_repairs_or_overwrites_source() -> None:
    source = {
        "programme_id": "OVC-PG-v0.2",
        "status": "QA_REVIEW",
        "current_packet": "PG-WP2",
        "current_gate": "PG-G2",
        "blockers": [],
        "next_action": "RUN_QA",
    }
    projection = {
        "programme_id": "OVC-PG-v0.2",
        "status": "RUNNING",
        "current_packet": "PG-WP2",
        "current_gate": "PG-G2",
        "blockers": [],
        "next_action": None,
    }
    result = compare_programme_state(source, projection, source_commit="a" * 40, projection_source_commit="b" * 40)
    assert result["effective_state"] == source
    assert result["repair_performed"] is False
    assert result["enforcement_allowed"] is False
    assert result["status"] == "CONFLICT"
    finding_types = {finding["finding_type"] for finding in result["findings"]}
    assert {"STALE_PROJECTION", "STATE_SOURCE_CONFLICT"}.issubset(finding_types)


def test_ledger_contract_preserves_disabled_authority() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "append only" in text
    assert "programme-owned machine-readable state is the effective state" in text
    assert "enforcement remains disabled before `PG-G6`" in text
    assert "PG-G3A" in text
    assert "Never rewrite the ledger or programme-owned state" in text
