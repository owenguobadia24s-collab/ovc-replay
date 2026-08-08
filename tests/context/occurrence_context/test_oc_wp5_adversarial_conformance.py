import json
from copy import deepcopy
from pathlib import Path
import unittest

from ovc.context.occurrence_context.builder import OccurrenceContextError, build_context, build_occurrence_key
from ovc.context.occurrence_context.calendar_adapter import assert_session_not_guessed, session_context_for_interval
from ovc.context.occurrence_context.chronology import assert_not_backdated
from ovc.context.occurrence_context.consumers import (
    assert_c2p_identity_payload_context_free,
    project_context,
    validate_consumption_manifest,
)
from ovc.context.occurrence_context.firewall import upstream_fingerprint
from ovc.context.occurrence_context.mcarb_refs import build_mcarb_context_ref
from ovc.context.occurrence_context.models import BuildRequest, ContextDependencyRef, OccurrenceAnchorRef
from ovc.context.occurrence_context.research_operations import research_operations_projection
from ovc.context.occurrence_context.supersession import create_supersession
from ovc.context.occurrence_context.c2e_adapter import episode_relative_context
from ovc.opt_b.c2e_v2.models import build_record

ROOT = Path(__file__).resolve().parents[3]
AUX_REGISTRY = json.loads((ROOT / "registries/context/occurrence_context/AUXILIARY_ADMISSION_REGISTRY_v0_1.json").read_text())
CONSUMERS = json.loads((ROOT / "registries/context/occurrence_context/CONSUMER_MANIFEST_REGISTRY_v0_1.json").read_text())


def dep(record_id="D1", fvt="2026-01-01T00:15:00Z"):
    return ContextDependencyRef(
        dependency_kind="SOURCE",
        record_id=record_id,
        schema_id="fixture/source/v1",
        logical_hash=f"sha256:{record_id.lower()}",
        first_valid_time=fvt,
        dependency_role="SOURCE",
        required=True,
    )


def anchor(kind="C2_OBSERVATION", structural=None):
    return OccurrenceAnchorRef(
        anchor_kind=kind,
        anchor_id="STRUCTURE.001" if not kind.startswith("SRI_") else "SRI.001",
        anchor_schema_id="fixture/anchor/v1",
        anchor_logical_hash="sha256:structure001" if not kind.startswith("SRI_") else "sha256:sri001",
        anchor_first_valid_time="2026-01-01T00:15:00Z",
        source_release_id="FIXTURE.R1",
        structural_anchor_ref=structural,
    )


def request(
    *,
    session_ids=(),
    registry="REG.v1",
    dependencies=None,
    lineage=None,
    role="DISCOVERY",
    authority_state="SHADOW",
    availability="AVAILABLE",
    reasons=(),
    auxiliary=(),
    episode=None,
    anchor_ref=None,
    confirmation="2026-01-01T00:15:00Z",
):
    return BuildRequest(
        anchor_ref=anchor_ref or anchor(),
        source_context={"instrument_id":"GBPUSD","price_side":"BID","source_release_id":"FIXTURE.R1","manifest_id":"FIXTURE.M1"},
        research_role=role,
        occurrence_interval={"start":"2026-01-01T00:00:00Z","end":"2026-01-01T00:15:00Z"},
        calendar_context={"calendar_year":2026,"calendar_month":1,"calendar_quarter":1,"era_partition_ids":[]},
        session_context={"session_membership_ids":list(session_ids),"a_l_block_id":None,"registry_id":registry},
        clock_scale_context={"clock_id":"15M","scale_id":"15M","lattice_id":None,"canonical_clock_position":None},
        confirmation_time=confirmation,
        dependency_refs=tuple(dependencies or (dep(),)),
        registry_bindings={"calendar_session_registry_id":registry},
        registry_first_valid_times=("2025-12-31T00:00:00Z",),
        availability_status=availability,
        reason_codes=tuple(reasons),
        authority_state=authority_state,
        lineage=lineage or {"builder":"WP5_FIXTURE"},
        auxiliary_refs=tuple(auxiliary),
        episode_relative_context=episode,
    )


def manifest(kind):
    return next(item for item in CONSUMERS["manifests"] if item["consumer_kind"] == kind)


def mcarb_payload():
    return {
        "kind":"ACTIVITY_LIQUIDITY",
        "record_id":"MCARB.FIXTURE.001",
        "record_schema_id":"mcarb_fixture/v1",
        "record_logical_hash":"sha256:mcarb001",
        "candidate_or_pack_id":"MCARB.FIXTURE.PACK",
        "candidate_or_pack_version":"0.1",
        "first_valid_time":"2026-01-01T00:15:00Z",
        "availability_status":"AVAILABLE",
        "qualification_record_id":"QUAL.FIXTURE.001",
        "qualification_status":"FIXTURE_ONLY",
    }


def c2e_records(status="CENSORED"):
    genesis = build_record("episode_genesis", {
        "boundary_pack_id":"C2E.BOUNDARY.FIXTURE","source_release_id":"R1","instrument_id":"GBPUSD","side":"BID","scope_id":"GBPUSD-15M-LOCAL-v0.1","scale_id":"15M","birth_frame_id":"F1","birth_boundary_rule_id":"BIRTH","birth_effective_time":"2026-01-01T00:00:00Z","first_valid_time":"2026-01-01T00:15:00Z","authority":"INACTIVE_NONCANONICAL_SHADOW"
    })
    snapshot = build_record("episode_snapshot", {
        "episode_id":genesis["episode_id"],"as_of_time":"2026-01-01T00:30:00Z","first_valid_time":"2026-01-01T00:30:00Z","status":status,"member_ids":["F1","F2"],"phase_segment_ids":[],"boundary_event_ids":[],"authority":"INACTIVE_NONCANONICAL_SHADOW"
    })
    return genesis, snapshot


class OCWP5AdversarialConformanceTests(unittest.TestCase):
    def test_f01_identical_structure_different_sessions_same_occurrence(self):
        asia = build_context(request(session_ids=("ASIA",), registry="REG.A"))
        london = build_context(request(session_ids=("LONDON",), registry="REG.B"))
        self.assertEqual(asia["occurrence_key"], london["occurrence_key"])
        self.assertNotEqual(asia["occurrence_context_id"], london["occurrence_context_id"])

    def test_f02_later_context_evidence_creates_successor(self):
        prior = build_context(request(registry="REG.v1"))
        before = deepcopy(prior)
        successor = build_context(request(registry="REG.v2", confirmation="2026-01-01T00:20:00Z"))
        link = create_supersession(prior, successor, "OC_REGISTRY_SESSION_STALE", changed_registry_ids=["REG.v1","REG.v2"])
        self.assertEqual(prior, before)
        self.assertEqual(link["prior_occurrence_context_id"], prior["occurrence_context_id"])

    def test_f03_outcome_and_future_fields_cannot_enter_context(self):
        for field in ("outcome","future_return","mfe","mae","probability","risk","exposure","execution"):
            with self.assertRaisesRegex(ValueError, "OC_DEP_FORBIDDEN_FIELD"):
                build_context(request(lineage={field:"FORBIDDEN"}))

    def test_f04_mcarb_vectors_cannot_be_silently_embedded(self):
        raw_ref = mcarb_payload()
        raw_ref["vector"] = ["1","2"]
        with self.assertRaisesRegex(ValueError, "OC_DEP_FORBIDDEN_FIELD"):
            build_context(request(auxiliary=(raw_ref,)))
        with self.assertRaises(OccurrenceContextError):
            build_mcarb_context_ref(raw_ref, AUX_REGISTRY, fixture_only=True)

    def test_f05_elapsed_duration_requires_lawful_c2e_anchor(self):
        with self.assertRaises(OccurrenceContextError) as caught:
            build_context(request(episode={"elapsed_duration":"PT900S"}))
        self.assertEqual(caught.exception.reason_code, "OC_C2E_REQUIRED_FOR_ELAPSED_DURATION")

    def test_f06_context_aware_representation_rejected_without_admission(self):
        bad = deepcopy(manifest("SRI_RESEARCH"))
        bad["field_dependencies"].append({"field_path":"clock_scale_context.clock_id","dependency":"OPTIONAL","role":"REPRESENTATION_INPUT"})
        with self.assertRaises(OccurrenceContextError) as caught:
            validate_consumption_manifest(bad)
        self.assertEqual(caught.exception.reason_code, "OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED")

    def test_f07_registry_change_preserves_historical_interpretation(self):
        v1 = build_context(request(registry="REG.v1"))
        v2 = build_context(request(registry="REG.v2", confirmation="2026-01-01T00:16:00Z"))
        self.assertEqual(v1["occurrence_key"], v2["occurrence_key"])
        self.assertNotEqual(v1["occurrence_context_id"], v2["occurrence_context_id"])
        self.assertEqual(v1["session_context"]["registry_id"], "REG.v1")

    def test_f08_validation_occurrence_anchor_is_inaccessible(self):
        with self.assertRaises(OccurrenceContextError) as caught:
            build_context(request(role="VALIDATION_METADATA_ONLY"))
        self.assertEqual(caught.exception.reason_code, "OC_AUTH_VALIDATION_ACCESS_DENIED")

    def test_f09_parent_first_valid_after_proposed_child_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "OC_TIME_BACKDATE_DENIED"):
            assert_not_backdated("2026-01-01T00:15:00Z", ["2026-01-01T00:16:00Z"])

    def test_f10_censored_episode_is_never_completion(self):
        genesis, snapshot = c2e_records("CENSORED")
        relative = episode_relative_context(genesis, snapshot)
        self.assertIsNotNone(relative["censoring_context"])
        self.assertIsNone(relative["completion_context"])

    def test_f11_alias_anchor_requires_exact_structural_lineage(self):
        malformed = anchor("SRI_OCCURRENCE_REPRESENTATION", structural={"anchor_kind":"C2_OBSERVATION"})
        with self.assertRaises(OccurrenceContextError) as caught:
            build_occurrence_key(malformed)
        self.assertEqual(caught.exception.reason_code, "OC_ID_ANCHOR_MUTATION")

    def test_f12_path_hostname_worker_and_dependency_order_do_not_change_record(self):
        d1, d2 = dep("D1"), dep("D2")
        a = build_context(request(dependencies=(d1,d2,d1), lineage={"builder":"FIXED","path":"/tmp/a","hostname":"one","worker_id":"A","pid":1}))
        b = build_context(request(dependencies=(d2,d1), lineage={"builder":"FIXED","path":"C:/other","hostname":"two","worker_id":"B","pid":999}))
        self.assertEqual(a["occurrence_context_id"], b["occurrence_context_id"])
        self.assertEqual(a["logical_hash"], b["logical_hash"])
        self.assertEqual(a["dependency_refs"], b["dependency_refs"])
        self.assertNotIn("path", a["lineage"])
        self.assertNotIn("hostname", a["lineage"])

    def test_f13_missing_optional_mcarb_reference_is_explicit_partial(self):
        built = build_context(request(availability="PARTIAL", reasons=("OC_MCARB_REF_UNAVAILABLE",), auxiliary=()))
        self.assertEqual(built["availability"]["status"], "PARTIAL")
        self.assertIn("OC_MCARB_REF_UNAVAILABLE", built["reason_codes"])

    def test_f14_unavailable_session_registry_never_guesses(self):
        session = session_context_for_interval("2026-01-01T00:00:00Z")
        self.assertEqual(session["status"], "UNAVAILABLE")
        self.assertEqual(session["session_membership_ids"], [])
        self.assertIsNone(session["a_l_block_id"])
        assert_session_not_guessed(session)

    def test_f15_undeclared_or_whole_envelope_consumption_fails_closed(self):
        built = build_context(request())
        bad = deepcopy(manifest("C25_FUTURE_STUB"))
        bad["field_dependencies"] = [{"field_path":"*","dependency":"OPTIONAL","role":"DISPLAY_ONLY"}]
        with self.assertRaises(OccurrenceContextError) as caught:
            project_context(built, bad)
        self.assertEqual(caught.exception.reason_code, "OC_ROLE_UNDECLARED_FIELD")

    def test_f16_c2p_identity_contamination_is_rejected(self):
        assert_c2p_identity_payload_context_free({"structural_object_id":"S1","genesis_id":"G1"})
        with self.assertRaises(OccurrenceContextError) as caught:
            assert_c2p_identity_payload_context_free({"structural_object_id":"S1","occurrence_context_id":"OC1"})
        self.assertEqual(caught.exception.reason_code, "OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED")

    def test_consumer_registry_covers_all_required_interfaces(self):
        kinds = {item["consumer_kind"] for item in CONSUMERS["manifests"]}
        self.assertEqual(kinds, {"SRI_RESEARCH","FDI_C2G_RESEARCH","C2P_FUTURE_STUB","C25_FUTURE_STUB","C3_FUTURE_STUB","RESEARCH_OPERATIONS_READ_ONLY"})
        self.assertEqual(CONSUMERS["representation_input_manifests"], [])
        self.assertEqual(CONSUMERS["c2p_runtime"], "NOT_STARTED")

    def test_read_only_research_operations_projection_is_detached(self):
        built = build_context(request())
        before = deepcopy(built)
        projection = research_operations_projection(built, manifest("RESEARCH_OPERATIONS_READ_ONLY"))
        projection["projection"]["fields"]["source_context.instrument_id"] = "MUTATED_COPY"
        self.assertEqual(built, before)
        self.assertEqual(projection["write_authority"], "NONE")

    def test_upstream_mutation_sentinel(self):
        upstream = {"c2_state_id":"C2.1","logical":"immutable"}
        before = upstream_fingerprint(upstream)
        build_context(request())
        self.assertEqual(before, upstream_fingerprint(upstream))

    def test_unknown_new_instrument_side_and_activating_authority_denied(self):
        base = request()
        with self.assertRaises(OccurrenceContextError):
            build_context(BuildRequest(**{**base.__dict__, "source_context": {**base.source_context, "instrument_id":"XAUUSD"}}))
        with self.assertRaises(OccurrenceContextError):
            build_context(BuildRequest(**{**base.__dict__, "source_context": {**base.source_context, "price_side":"MID"}}))
        with self.assertRaises(OccurrenceContextError):
            build_context(request(authority_state="ACTIVE"))

    def test_conflicting_or_guessed_session_membership_is_denied_by_current_registry(self):
        with self.assertRaises(OccurrenceContextError):
            assert_session_not_guessed({"session_membership_ids":["ASIA","LONDON"],"a_l_block_id":"D"})


if __name__ == "__main__":
    unittest.main()
