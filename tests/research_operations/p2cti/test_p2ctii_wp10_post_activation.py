from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.research_operations.p2cti.intake import build_theory_seed
from ovc.research_operations.p2cti.post_activation import (
    PostActivationError,
    build_operational_monitoring_ledger,
    build_operational_observation,
    evaluate_operational_incidents,
    rehearse_isolated_write,
)
from ovc.research_operations.p2cti.work import build_work_ticket

COMMIT = "a0390ee0650fad2caf1311923c333e1d933fc61e"
TREE = "446f69d74b9e3a444f82965603ed05f2ba99441d"
GENERATION = "p2cti:generation:4517d24b230da9e29af072ca9ed680943bbf598cf2382f18ccf3f9ba8b9099e9"
FRONTIER = "p2cti:frontier:77787699affb040f469551a59eea5e2ee841d51f6a69287dae06055c74d5a659"
ACTIVATION = "docs/programmes/p2cti-v0-1/wp9/P2CTII_G_OBSERVABILITY_ACTIVATE_ACTIVATION_RECEIPT_v0_1.json"

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/p2cti/P2CTII_WP10_POST_ACTIVATION_FIXTURE_v0_1.json"


def test_wp10_fixture_binds_exact_activation_and_forbids_durable_target() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["repository_commit"] == COMMIT
    assert fixture["repository_tree"] == TREE
    assert fixture["generation_id"] == GENERATION
    assert fixture["source_frontier_id"] == FRONTIER
    assert fixture["activation_receipt_ref"] == ACTIVATION
    assert fixture["forbidden_durable_target"] == "records/research_operations/p2cti/live"
    assert fixture["authority_effect"] == "NONE"


def _observation(**overrides):
    values = {
        "repository_commit": COMMIT,
        "repository_tree": TREE,
        "generation_id": GENERATION,
        "source_frontier_id": FRONTIER,
        "currentness_state": "CURRENT",
        "reference_optimized_equivalent": True,
        "protected_source_leak_count": 0,
        "index_integrity_ok": True,
        "activation_receipt_ref": ACTIVATION,
        "warnings": (),
    }
    values.update(overrides)
    return build_operational_observation(**values)


def test_post_activation_observation_is_read_only_operational_and_stable() -> None:
    observation = _observation()
    assert observation["operational_reliance"] is True
    assert observation["read_only"] is True
    assert observation["durable_write_effect"] is False
    assert observation["authority_effect"] == "NONE"
    evaluation = evaluate_operational_incidents(observation)
    assert evaluation["status"] == "PASS_OPERATIONAL_STABLE"
    assert evaluation["incident_classes"] == []
    assert evaluation["continue_operational_reliance"] is True
    assert evaluation["automatic_authority_expansion"] is False


@pytest.mark.parametrize(
    ("overrides", "incident"),
    [
        ({"currentness_state": "STALE"}, "FALSE_CURRENTNESS"),
        ({"currentness_state": "UNRESOLVED"}, "SOURCE_FRONTIER_UNRESOLVED"),
        ({"protected_source_leak_count": 1}, "PROTECTED_SOURCE_LEAK"),
        ({"reference_optimized_equivalent": False}, "REFERENCE_OPTIMIZED_DIVERGENCE"),
        ({"index_integrity_ok": False}, "INDEX_CORRUPTION"),
    ],
)
def test_post_activation_incidents_fail_closed_to_requalification(overrides: dict, incident: str) -> None:
    evaluation = evaluate_operational_incidents(_observation(**overrides))
    assert incident in evaluation["incident_classes"]
    assert evaluation["status"] == "REQUALIFICATION_REQUIRED"
    assert evaluation["required_action"] == "DISABLE_RELIANCE_AND_REQUALIFY"
    assert evaluation["continue_operational_reliance"] is False
    assert evaluation["authority_effect"] == "NONE"


def test_monitoring_ledger_is_order_independent_and_bounded() -> None:
    first = _observation()
    second = _observation(repository_commit="b" * 40, repository_tree="c" * 40)
    one = build_operational_monitoring_ledger([first, second])
    two = build_operational_monitoring_ledger([second, first])
    assert one == two
    assert one["all_stable"] is True
    assert one["operational_reliance_scope"] == "READ_ONLY_CURRENT_PROJECTION_ONLY"
    assert one["next_reserved_gate"] == "P2CTII-G-CONTINUOUS-INTAKE"
    assert one["durable_write_effect"] is False


def _synthetic_records():
    source_ref = {
        "source_id": "synthetic:wp10",
        "source_kind": "SYNTHETIC_REHEARSAL",
        "source_locator": "memory://p2ctii-wp10",
        "content_sha256": "d" * 64,
        "authority_refs": ["P2CTII-G-OBSERVABILITY-ACTIVATE-PASS"],
        "scientific_payload_copied": False,
    }
    seed = build_theory_seed(
        source_frontier_id=FRONTIER,
        seed_key="WP10-SYNTHETIC-SEED",
        title="Synthetic isolated intake rehearsal",
        source_ref=source_ref,
    )
    ticket = build_work_ticket(
        source_frontier_id=FRONTIER,
        ticket_key="WP10-SYNTHETIC-TICKET",
        subject_ref=seed["record_id"],
        work_class="THEORY_FORMALISATION",
        work_state="READY",
        authority_refs=["P2CTII-G-OBSERVABILITY-ACTIVATE-PASS"],
        created_at="2026-08-22T19:00:00Z",
    )
    return seed, ticket


def test_isolated_write_rehearsal_is_deterministic_and_never_durable() -> None:
    seed, ticket = _synthetic_records()
    one = rehearse_isolated_write([seed, ticket])
    two = rehearse_isolated_write([ticket, seed])
    assert one == two
    assert one["storage_scope"] == "EPHEMERAL_IN_MEMORY_ONLY"
    assert one["record_count"] == 2
    assert one["replay_equal"] is True
    assert one["durable_target"] is None
    assert one["durable_write_attempted"] is False
    assert one["durable_write_performed"] is False
    assert one["write_activation"] is False
    assert one["authority_effect"] == "NONE"


def test_isolated_write_rehearsal_rejects_durable_sink_and_mutation() -> None:
    seed, ticket = _synthetic_records()
    with pytest.raises(PostActivationError, match="durable targets are forbidden"):
        rehearse_isolated_write([seed, ticket], durable_target="records/research_operations/p2cti/live")
    mutated = copy.deepcopy(seed)
    mutated["payload"]["title"] = "mutated"
    with pytest.raises(PostActivationError, match="content hash mismatch"):
        rehearse_isolated_write([mutated])


def test_isolated_write_rehearsal_rejects_authority_or_write_activation() -> None:
    seed, _ = _synthetic_records()
    write_enabled = copy.deepcopy(seed)
    write_enabled["payload"]["write_activation"] = True
    from ovc.research_operations.canonical import canonical_sha256
    write_enabled["content_sha256"] = canonical_sha256({k: v for k, v in write_enabled.items() if k != "content_sha256"})
    with pytest.raises(PostActivationError, match="not synthetic/non-write"):
        rehearse_isolated_write([write_enabled])
