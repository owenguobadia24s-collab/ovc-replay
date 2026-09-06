from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ovc.research_operations.rrscg import (
    ConstraintViewEvidence,
    PRIMARY_CONSTRAINT_VIEWS,
    SOURCE_ARCHIVE_SHA256,
    build_constraint_population,
    compose_constraint_event,
    summarise_population,
)

TEST_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = TEST_ROOT.parent
ORACLE = TEST_ROOT / "fixtures/research_operations/rrscg/RRSCG_R2_REFERENCE_AND_ALGORITHMIC_ORACLE_v0_1.json"
KERNEL = REPO_ROOT / "src/ovc/research_operations/rrscg/kernel.py"
DOCS = REPO_ROOT / "docs/programmes/lsiac-v0-1/rrscg-core-wp1"
STATE = REPO_ROOT / "records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_23.json"
EXPECTED_R2 = "5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5"


@dataclass(frozen=True)
class FixtureEvent:
    event_id: str
    source_generation_id: str
    cohort: str
    segment_id: str
    iso_week: str
    source_order: int
    target_fvt: int
    path: tuple
    targets: tuple
    eligible: bool = True
    component_fvts: tuple = ()
    event_time_utc: str | None = None
    target_source_available: bool = True
    micro_path_applicability: str = "AUTO"
    previous_owner_available: bool = True
    censored: bool = False

    def target(self, pack_id):
        return dict(self.targets)[pack_id]


def _targets(label):
    return (
        ("T0_v1", ("T0", label)),
        ("T1_v1", ("T1", label)),
        ("R18_MID_v1", ("MID", label)),
        ("ETR_v1", ("ETR", label)),
        ("T2_v1", ("T2", label)),
        ("T3_v1", ("T3", label)),
    )


def _synthetic_interval(
    i,
    cohort="TRAIN",
    target_label="A",
    carrier_seed=0,
    operation=1,
    segment_id="S1",
    iso_week="W1",
    path_length=1,
):
    path = []
    for j in range(path_length):
        vals = (
            carrier_seed % 3,
            (carrier_seed + j) % 2,
            (carrier_seed + j) % 4,
            (carrier_seed + j) % 3,
            (carrier_seed + j) % 2,
            (carrier_seed + j) % 2,
        )
        carrier = tuple(("UNCHANGED", int(x)) for x in vals)
        op_code = int(operation if j == path_length - 1 else (operation + j) % 3)
        path.append((carrier, (op_code,)))
    return FixtureEvent(
        event_id=f"E{i:05d}",
        source_generation_id="SYNTH_RRSCG_v1",
        cohort=cohort,
        segment_id=segment_id,
        iso_week=iso_week,
        source_order=i,
        target_fvt=1000 + i,
        path=tuple(path),
        targets=_targets(target_label),
        eligible=True,
        component_fvts=tuple(900 + i + j for j in range(path_length)),
        event_time_utc=f"2026-01-{1 + (i % 20):02d}T00:00:00+00:00",
        target_source_available=True,
        micro_path_applicability="MICRO_BEARING",
        previous_owner_available=True,
        censored=False,
    )


def _world():
    pattern = ("A", "B", "A", "A")
    train = [
        _synthetic_interval(
            i, "TRAIN", pattern[i % 4], carrier_seed=i % 4, operation=i % 2, iso_week="W1"
        )
        for i in range(8)
    ]
    evals = [
        _synthetic_interval(
            100 + j,
            "EVAL",
            pattern[j % 4],
            carrier_seed=j % 4,
            operation=j % 2,
            iso_week="W2",
        )
        for j in range(4)
    ]
    evals.append(
        _synthetic_interval(
            199, "EVAL", "A", carrier_seed=0, operation=0, iso_week="W2", path_length=0
        )
    )
    return train, evals


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _function_ast_sha256(text: str, name: str) -> str:
    tree = ast.parse(text)
    node = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    )
    payload = ast.dump(node, include_attributes=False, annotate_fields=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_exact_bound_source_identity_and_population_oracle():
    oracle = _load(ORACLE)
    assert oracle["source_zip_sha256"] == SOURCE_ARCHIVE_SHA256 == EXPECTED_R2
    assert oracle["source_package"] == {
        "internal_sha256sum_entries_verified": 75,
        "package_tests_passed": 14,
    }

    train, evals = _world()
    constraints = build_constraint_population(train, evals)
    expected = oracle["synthetic_case"]

    representative = constraints[expected["representative_event"]]
    assert {v.view_id: v.antecedent_support for v in representative.views} == (
        expected["representative_antecedent_support_by_view"]
    )
    assert {
        v.view_id: [[k, n] for k, n in v.qualified_frontier_supports]
        for v in representative.views
    } == expected["representative_qualified_frontier_by_view"]
    assert all(v.training_frontier_id == expected["training_frontier_id"] for v in representative.views)

    for event_id, row in expected["constraints"].items():
        c = constraints[event_id]
        assert c.constraint_id == row["constraint_id"]
        assert c.state == row["state"]
        assert c.full_consensus_state == row["full_consensus_state"]
        assert c.selected_resolution_tier == row["selected_resolution_tier"]
        assert sorted(c.selected_frontier) == row["selected_frontier"]
        assert c.full_viewset_supported == row["full_viewset_supported"]
        assert c.relation_resolved == row["relation_resolved"]

    summary, evaluations = summarise_population(evals, constraints)
    population = expected["population"]
    assert summary.summary_id == population["summary_id"]
    assert summary.n_total == population["n_total"]
    assert summary.n_full_viewset_supported == population["n_full_viewset_supported"]
    assert summary.n_relation_resolved == population["n_relation_resolved"]
    assert summary.selected_hit_rate == population["selected_hit_rate"]
    assert summary.selected_efficiency == population["selected_efficiency"]
    assert summary.mean_single_view_efficiency == population["mean_single_view_efficiency"]
    assert summary.consensus_advantage == population["consensus_advantage"]
    assert [list(x) for x in summary.selected_tier_counts] == population["selected_tier_counts"]

    by_event = {x.event_id: x for x in evaluations}
    for event_id, row in expected["evaluations"].items():
        x = by_event[event_id]
        assert x.evaluation_id == row["evaluation_id"]
        assert x.target_id == row["target_id"]
        assert x.selected_hit == row["selected_hit"]
        assert x.selected_size == row["selected_size"]
        assert x.selected_efficiency == row["selected_efficiency"]
        assert x.mean_single_view_efficiency == row["mean_single_view_efficiency"]
        assert x.consensus_advantage == row["consensus_advantage"]


def _compose_case_inputs(case_id):
    def view(view_id, members, supported=True):
        fs = tuple((member, 3) for member in members)
        return ConstraintViewEvidence(
            view_id, supported, 5, fs, fs, "R18_MID_v1", 2, "TF", "SRC"
        )

    cases = {
        "full_consensus": [
            view("C_LAST_EXACT", ("A", "B", "C")),
            view("C_LAST_HI", ("A", "B", "D")),
            view("C_LAST_MID", ("A", "B", "E")),
            view("CARRIER_BAG_HI", ("A", "C", "D")),
            view("CARRIER_BAG_MID", ("A", "B", "F")),
        ],
        "coarse_consensus": [
            view("C_LAST_EXACT", ("X",)),
            view("C_LAST_HI", ("A",)),
            view("C_LAST_MID", ("A",)),
            view("CARRIER_BAG_HI", ("Y",)),
            view("CARRIER_BAG_MID", ("A",)),
        ],
        "minimal_constraint": [
            view("C_LAST_EXACT", (), False),
            view("C_LAST_HI", ("X",)),
            view("C_LAST_MID", ("A",)),
            view("CARRIER_BAG_HI", ("Y",)),
            view("CARRIER_BAG_MID", ("Z",)),
        ],
        "abstain": [
            view("C_LAST_EXACT", (), False),
            view("C_LAST_HI", (), False),
            view("C_LAST_MID", (), False),
            view("CARRIER_BAG_HI", (), False),
            view("CARRIER_BAG_MID", (), False),
        ],
    }
    return cases[case_id]


def test_exact_compose_oracle_covers_all_resolution_states():
    oracle = _load(ORACLE)
    seen = set()
    for case_id, row in oracle["compose_cases"].items():
        result = compose_constraint_event("E", "SRC", _compose_case_inputs(case_id))
        assert result.constraint_id == row["constraint_id"]
        assert result.state == row["state"]
        assert result.full_consensus_state == row["full_consensus_state"]
        assert result.selected_resolution_tier == row["selected_resolution_tier"]
        assert sorted(result.selected_frontier) == row["selected_frontier"]
        assert sorted(result.full_core) == row["full_core"]
        assert sorted(result.majority) == row["majority"]
        assert sorted(result.envelope) == row["envelope"]
        assert sorted(result.shell) == row["shell"]
        assert [list(x) for x in result.consensus_counts] == row["consensus_counts"]
        seen.add(result.state)
    assert seen == {
        "RESOLVED_FULL_CONSENSUS",
        "RESOLVED_COARSE_CONSENSUS",
        "RESOLVED_MINIMAL_CONSTRAINT",
        "ABSTAIN_NO_CONSTRAINT",
    }


def test_path_missingness_fails_closed_to_abstention():
    train, evals = _world()
    missing = build_constraint_population(train, evals)["E00199"]
    assert missing.full_viewset_supported is False
    assert missing.relation_resolved is False
    assert missing.selected_resolution_tier is None
    assert missing.selected_frontier == frozenset()
    assert missing.state == "ABSTAIN_NO_CONSTRAINT"
    assert all(v.supported is False and v.antecedent_support == 0 for v in missing.views)


def test_primary_record_excludes_operation_and_order_identity():
    views = []
    for view_id in PRIMARY_CONSTRAINT_VIEWS:
        fs = (("A", 3),)
        views.append(ConstraintViewEvidence(view_id, True, 5, fs, fs, "R18_MID_v1", 2, "TF", "SRC"))
    result = compose_constraint_event("E", "SRC", views)
    assert not hasattr(result, "last_operation")
    assert not hasattr(result, "operation_path")
    assert not hasattr(result, "factor_path_order")


def test_twenty_load_bearing_function_bodies_match_exact_source_ast_fingerprints():
    oracle = _load(ORACLE)
    fingerprints = oracle["algorithmic_fingerprints"]
    assert fingerprints["all_function_body_ast_identities_match"] is True
    assert fingerprints["comparison_count"] == 20
    text = KERNEL.read_text(encoding="utf-8")
    for name, row in fingerprints["functions"].items():
        assert _function_ast_sha256(text, name) == row["source_ast_sha256"]


def test_source_rematerialisation_closes_only_execution_availability_blocker():
    receipt = _load(DOCS / "RRSCG_CORE_WP1_SOURCE_REMATERIALISATION_RECEIPT_v0_1.json")
    frontier = _load(DOCS / "RRSCG_CORE_WP1_DEPENDENCY_FRONTIER_v0_2.json")
    assert receipt["expected_sha256"] == receipt["actual_sha256"] == EXPECTED_R2
    assert receipt["sha256_match"] is True
    assert receipt["internal_sha256sum_entries_verified"] == 75
    assert receipt["exact_source_package_tests"] == "14_PASSED"
    assert frontier["blocked"] == []


def test_g1_pass_is_non_reserved_and_keeps_capability_inactive():
    decision = _load(DOCS / "RRSCG_CORE_G1_GATE_DECISION_v0_1.json")
    authority = _load(DOCS / "RRSCG_CORE_WP1_AUTHORITY_MANIFEST_v0_2.json")
    state = _load(STATE)
    assert decision["decision"] == "PASS"
    assert decision["decision_class"] == "DELEGATED_AUTO_RATIFICATION_NON_RESERVED_CONFORMANCE"
    assert decision["authority_delta"] == "NONE"
    assert decision["activation_effect"] == "NONE_CAPABILITY_REMAINS_INACTIVE"
    assert state["status"] == "APPROVED"
    assert state["operator_decision_required_now"] is False
    assert state["capability_activation_allowed"] is False
    assert state["next_packet"] == "RRSCG-CORE-WP2-D9-OBSERVER-STATE-FACULTY"
    denied = set(authority["denied"])
    assert {"CAPABILITY_ACTIVATION", "ACTIVE_VALIDATION", "CANONICAL_OR_R2_PUBLICATION",
            "PROBABILITY_RISK_EXPOSURE_EH_TRADING_OR_EXECUTION_AUTHORITY"} <= denied
