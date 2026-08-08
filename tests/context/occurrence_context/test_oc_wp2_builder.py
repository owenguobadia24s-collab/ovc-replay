from copy import deepcopy
import unittest

from ovc.context.occurrence_context import (
    BuildRequest,
    ContextDependencyRef,
    OccurrenceAnchorRef,
    OccurrenceContextError,
    build_context,
    build_occurrence_key,
    create_supersession,
    replay_contexts,
)
from ovc.context.occurrence_context.serialization import canonical_json


def anchor(kind="C2_OBSERVATION"):
    return OccurrenceAnchorRef(
        anchor_kind=kind,
        anchor_id="STRUCTURE.001",
        anchor_schema_id="fixture/c2/v1",
        anchor_logical_hash="sha256:structure001",
        anchor_first_valid_time="2026-01-01T00:15:00Z",
        source_release_id="FIXTURE.RELEASE.001",
    )


def dependency(record_id="TIME.001", fvt="2026-01-01T00:15:00Z"):
    return ContextDependencyRef(
        dependency_kind="TIME_COORDINATE",
        record_id=record_id,
        schema_id="fixture/time/v1",
        logical_hash="sha256:" + record_id.lower().replace(".", ""),
        first_valid_time=fvt,
        dependency_role="SOURCE",
        required=True,
    )


def request(*, session="S1", dep=None, confirmation="2026-01-01T00:15:00Z", registry="REG.v1", role="DISCOVERY", episode=None, market=None):
    return BuildRequest(
        anchor_ref=anchor(),
        source_context={"instrument_id":"GBPUSD","price_side":"BID","source_release_id":"FIXTURE.RELEASE.001","manifest_id":"FIXTURE.MANIFEST.001"},
        research_role=role,
        occurrence_interval={"start":"2026-01-01T00:00:00Z","end":"2026-01-01T00:15:00Z"},
        calendar_context={"calendar_year":2026,"calendar_month":1,"calendar_quarter":1},
        session_context={"session_membership_ids":[session],"a_l_block_id":None,"registry_id":registry},
        clock_scale_context={"clock_id":"15M","scale_id":"15M","lattice_id":None,"canonical_clock_position":None},
        confirmation_time=confirmation,
        dependency_refs=(dep or dependency(),),
        registry_bindings={"calendar_session_registry_id":registry},
        registry_first_valid_times=("2025-12-31T00:00:00Z",),
        availability_status="AVAILABLE",
        reason_codes=(),
        authority_state="SHADOW",
        lineage={"builder":"test"},
        episode_relative_context=episode,
        market_condition_context=market,
    )


class OCWP2BuilderTests(unittest.TestCase):
    def test_structure_identity_is_context_independent(self):
        first = build_context(request(session="ASIA", dep=dependency("TIME.ASIA"), registry="REG.A"))
        second = build_context(request(session="LONDON", dep=dependency("TIME.LONDON"), registry="REG.B"))
        self.assertEqual(first["occurrence_key"], second["occurrence_key"])
        self.assertNotEqual(first["occurrence_context_id"], second["occurrence_context_id"])
        self.assertEqual(build_occurrence_key(anchor()), first["occurrence_key"])

    def test_later_registry_creates_successor_not_rewrite(self):
        prior = build_context(request(registry="REG.v1"))
        prior_copy = deepcopy(prior)
        successor = build_context(request(registry="REG.v2", confirmation="2026-01-01T00:20:00Z"))
        link = create_supersession(prior, successor, "OC_REGISTRY_SESSION_STALE", changed_registry_ids=["REG.v1", "REG.v2"])
        self.assertEqual(prior, prior_copy)
        self.assertEqual(link["prior_occurrence_context_id"], prior["occurrence_context_id"])
        self.assertEqual(link["successor_occurrence_context_id"], successor["occurrence_context_id"])

    def test_forbidden_future_field_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "OC_DEP_FORBIDDEN_FIELD"):
            build_context(request(market={"future_return": "forbidden"}))

    def test_elapsed_duration_requires_c2e(self):
        with self.assertRaises(OccurrenceContextError) as caught:
            build_context(request(episode={"elapsed_duration":"PT15M"}))
        self.assertEqual(caught.exception.reason_code, "OC_C2E_REQUIRED_FOR_ELAPSED_DURATION")

    def test_validation_occurrence_access_is_denied(self):
        with self.assertRaises(OccurrenceContextError) as caught:
            build_context(request(role="VALIDATION_METADATA_ONLY"))
        self.assertEqual(caught.exception.reason_code, "OC_AUTH_VALIDATION_ACCESS_DENIED")

    def test_first_valid_is_max_of_all_dependencies(self):
        built = build_context(request(dep=dependency("TIME.LATE", "2026-01-01T00:17:00Z"), confirmation="2026-01-01T00:16:00Z"))
        self.assertEqual(built["first_valid_time"], "2026-01-01T00:17:00Z")

    def test_rebuild_and_replay_are_order_deterministic(self):
        a = request(session="A", dep=dependency("TIME.A"), registry="REG.A")
        b = request(session="B", dep=dependency("TIME.B"), registry="REG.B")
        self.assertEqual(build_context(a), build_context(a))
        self.assertEqual(replay_contexts([a, b]), replay_contexts([b, a]))

    def test_builder_does_not_mutate_inputs(self):
        source = {"instrument_id":"GBPUSD","price_side":"ASK","source_release_id":"R","manifest_id":"M"}
        calendar = {"calendar_year":2026,"calendar_month":1,"calendar_quarter":1}
        before_source, before_calendar = deepcopy(source), deepcopy(calendar)
        req = BuildRequest(anchor_ref=anchor(), source_context=source, research_role="DEVELOPMENT", occurrence_interval={"start":"2026-01-01T00:00:00Z","end":None}, calendar_context=calendar, session_context={"session_membership_ids":[],"a_l_block_id":None,"registry_id":"OC.CALENDAR_SESSION_BINDINGS.v0.1"}, clock_scale_context={"clock_id":"15M","scale_id":"15M","lattice_id":None,"canonical_clock_position":None}, confirmation_time="2026-01-01T00:15:00Z", dependency_refs=(dependency(),), registry_bindings={"calendar_session_registry_id":"OC.CALENDAR_SESSION_BINDINGS.v0.1"}, authority_state="SHADOW")
        build_context(req)
        self.assertEqual(source, before_source)
        self.assertEqual(calendar, before_calendar)

    def test_alias_anchor_resolves_to_structural_identity(self):
        structural = anchor().to_dict()
        alias = OccurrenceAnchorRef(anchor_kind="SRI_OCCURRENCE_REPRESENTATION", anchor_id="SRI.001", anchor_schema_id="fixture/sri/v1", anchor_logical_hash="sha256:sri001", anchor_first_valid_time="2026-01-01T00:16:00Z", structural_anchor_ref=structural)
        self.assertEqual(build_occurrence_key(alias), build_occurrence_key(anchor()))

    def test_canonical_serialization_rejects_float(self):
        with self.assertRaises(TypeError):
            canonical_json({"bad": 0.1})


if __name__ == "__main__":
    unittest.main()
