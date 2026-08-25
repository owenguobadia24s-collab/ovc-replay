from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.debt import validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
WP4 = ROOT / "docs/programmes/grt-v0-2/wp4"
IMPL = ROOT / "registries/implementation/grt_v0_2"
GOV = ROOT / "registries/governance/grt_v0_2"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_logical(record):
    payload = dict(record)
    logical_sha256 = payload.pop("logical_sha256")
    assert logical_sha256 == canonical_sha256(payload)


def test_wp4_entry_and_current_truth_are_exact():
    record = load(WP4 / "GRT2_WP4_CURRENT_TRUTH_CLASSIFICATION.json")
    check_logical(record)
    assert record["operator_instruction"] == "OVC RUN GRT2-WP4"
    assert record["baseline_commit"] == "953a24e268f07be27a20f47d06742ba718065441"
    assert record["g3_completion"]["completion_receipt_id"] == "fb290dbd049943e74d596c201b99a45f87cfd3d2902a369a30f86d0a5da5c240"
    assert record["classification"]["g3_status"] == "COMPLETED_PHYSICALLY_MATERIALISED"
    assert record["classification"]["current_full_g3_finding_count"] == 1648


def test_wp4_classifies_and_parks_the_moving_projection_repair():
    record = load(WP4 / "GRT2_WP4_CURRENT_TRUTH_CLASSIFICATION.json")
    substitution = record["exact_current_projection_substitution"]
    assert substitution["inherited_current_state"].endswith("OVC_GRT2_STATE_v0_16_SUPERSEDING_GATE_READY.json")
    assert substitution["candidate_state"].endswith("OVC_GRT2_STATE_v0_18_WP4_G4_GATE_READY.json")
    assert substitution["disposition_under_active_grt_exact"] == "REJECTED_AS_NEW_OR_RECURRENT_PENDING_GRT2_G4"
    assert substitution["extent_change"] == "UNCHANGED"


def test_wp4_advances_the_immutable_floor_chain_exactly_once():
    floor = load(GOV / "debt_floors/GRT_DEBT_FLOOR_G1.json")
    validate_debt_floor(floor)
    assert floor["generation"] == 1
    assert floor["floor_hash"] == "4fdfaf281720232dbb0fd6c9496b2849d26f1e7107d559bba0e6efc51fe02d27"
    assert floor["predecessor_commit"] == "953a24e268f07be27a20f47d06742ba718065441"
    assert floor["predecessor_tree"] == "485e08ed6011d481af8557ca40c19aded2db590f"
    assert len(floor["open_grandfathered_findings"]) <= 1648


def test_wp4_preserves_pgn_and_wp5_firewalls():
    record = load(WP4 / "GRT2_WP4_CURRENT_TRUTH_CLASSIFICATION.json")
    gate = load(WP4 / "GRT2_G4_GATE_PACKET.json")
    check_logical(gate)
    assert record["classification"]["native_pgn_adoption_status"] == "DEFERRED_INDEFINITELY"
    assert record["classification"]["native_pgn_records_created"] == 0
    assert record["classification"]["wp5_interlock"] == "FORBIDDEN_UNTIL_GRT2_G4_PASS"
    assert gate["gate_class"] == "OPERATOR_REQUIRED"
    assert gate["exact_operator_command"] == "OVC APPROVE GRT2-G4 PASS"


def test_wp4_manifest_and_frontier_are_hash_bound():
    manifest = load(WP4 / "GRT2_WP4_AUTHORITY_MANIFEST.json")
    frontier = load(WP4 / "GRT2_WP4_DEPENDENCY_FRONTIER.json")
    assert manifest["authority_manifest_id"] == canonical_sha256(manifest["authority_manifest"])
    assert manifest["authority_manifest"]["authority_delta"] == "NONE_CURRENT_TRUTH_CLASSIFICATION_AND_G4_PREPARATION_ONLY"
    assert frontier["dependency_frontier_id"] == canonical_sha256(frontier["dependency_frontier"])
