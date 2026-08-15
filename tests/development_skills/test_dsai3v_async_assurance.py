from __future__ import annotations

from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path

from ovc.development.skills.async_assurance import (
    AA0_BACKGROUND_REUSABLE,
    AA2_MATERIALISATION_EDGE,
    CONTROLLER_IDENTITY,
    NO_REUSE,
    REUSE_IF_DEPENDENCIES_UNCHANGED,
    AssuranceFuture,
    AssuranceWakeSubscription,
    AsyncAssuranceStore,
    ConditionalMaterialisationIntent,
    REQUIRED_READINESS_KEYS,
    RequiredAssuranceSet,
    apply_completion_signal,
    evaluate_materialisation_intent,
    promote_speculative_successor,
    required_assurance_satisfied,
    reuse_after_frontier_change,
    selective_descendant_invalidation,
    should_continue_development,
    speculative_action_allowed,
    supersede_intent_for_assurance_set,
)
from ovc.development.skills.async_assurance_github import (
    GITHUB_PROVIDER_ADAPTER_ID,
    GitHubAssuranceObservation,
    provider_capabilities,
    reconcile_github_future,
    signal_from_observation,
)
from ovc.development.skills.vit_materialisation import (
    PhysicalMaterialisationTransaction,
    recover_unknown_write,
)

ROOT = Path(__file__).resolve().parents[2]


def make_future(**overrides: object) -> AssuranceFuture:
    fields: dict[str, object] = {
        "programme_id": "OVC-AA-TEST",
        "packet_id": "AA-PACKET-A",
        "payload_id": "payload-a",
        "assurance_profile_id": "profile-tests",
        "candidate_commit": "head-a",
        "provider_adapter_id": GITHUB_PROVIDER_ADAPTER_ID,
        "workflow_name": "tests",
        "run_id": "100",
        "check_name": "tests",
        "assurance_class": AA0_BACKGROUND_REUSABLE,
        "reuse_class": REUSE_IF_DEPENDENCIES_UNCHANGED,
        "dependency_scope": ("candidate_content",),
        "state": "RUNNING",
    }
    fields.update(overrides)
    return AssuranceFuture(**fields)


def make_observation(
    *,
    conclusion: str | None = "success",
    status: str = "completed",
    observed_at: str = "2026-08-15T09:00:00Z",
    candidate_commit: str = "head-a",
) -> GitHubAssuranceObservation:
    return GitHubAssuranceObservation(
        repository="owenguobadia24s-collab/ovc-replay",
        candidate_commit=candidate_commit,
        workflow_name="tests",
        run_id="100",
        check_name="tests",
        status=status,
        conclusion=conclusion,
        observed_at=observed_at,
    )


def readiness(**overrides: bool) -> dict[str, bool]:
    result = {key: True for key in REQUIRED_READINESS_KEYS}
    result.update(overrides)
    return result


def make_intent(assurance_set_id: str, *, operator_required: bool = False) -> ConditionalMaterialisationIntent:
    return ConditionalMaterialisationIntent(
        programme_id="OVC-AA-TEST",
        packet_id="AA-PACKET-A",
        payload_id="payload-a",
        vit_generation_id="vit-a",
        train_generation_id="train-a",
        expected_predecessor_commit="base-commit",
        expected_predecessor_tree="base-tree",
        expected_result_tree="result-tree",
        authority_manifest_id="authority-a",
        required_assurance_set_id=assurance_set_id,
        materialisation_profile="LIVE_PHYSICAL_MAIN",
        gate_class="AUTO_RATIFIABLE",
        operator_required=operator_required,
    )


class Dsai3vAsyncAssuranceTests(unittest.TestCase):
    def test_duplicate_completion_signal_is_idempotent(self) -> None:
        future = make_future()
        signal = signal_from_observation(future, make_observation())
        assert signal is not None
        once = apply_completion_signal(future, signal)
        twice = apply_completion_signal(once, signal)
        self.assertEqual(once, twice)
        self.assertEqual(once.state, "PASS")

    def test_missed_signal_is_recovered_by_reconciliation(self) -> None:
        recovered = reconcile_github_future(make_future(), [make_observation()])
        self.assertEqual(recovered.state, "PASS")

    def test_out_of_order_and_event_reference_paths_converge(self) -> None:
        future = make_future()
        observations = [
            make_observation(observed_at="2026-08-15T09:00:02Z"),
            make_observation(observed_at="2026-08-15T09:00:01Z"),
        ]
        reference = reconcile_github_future(future, observations)
        event_driven = future
        for observation in reversed(observations):
            signal = signal_from_observation(event_driven, observation)
            assert signal is not None
            event_driven = apply_completion_signal(event_driven, signal)
        self.assertEqual(reference, event_driven)

    def test_stale_green_cannot_satisfy_new_head(self) -> None:
        future = replace(make_future(), state="PASS", conclusion="success")
        stale = reuse_after_frontier_change(future, {"candidate_content"})
        self.assertEqual(stale.state, "STALE")
        new_head = make_future(candidate_commit="head-b")
        self.assertIsNone(signal_from_observation(new_head, make_observation(candidate_commit="head-a")))

    def test_required_assurance_set_change_supersedes_intent(self) -> None:
        future = make_future()
        first = RequiredAssuranceSet("OVC-AA-TEST", "AA-PACKET-A", "v1", (future.future_id,))
        second = RequiredAssuranceSet("OVC-AA-TEST", "AA-PACKET-A", "v2", (future.future_id,))
        old, new = supersede_intent_for_assurance_set(make_intent(first.assurance_set_id), second.assurance_set_id)
        self.assertEqual(old.state, "SUPERSEDED")
        self.assertEqual(old.superseded_by, new.intent_id)
        self.assertNotEqual(old.intent_id, new.intent_id)

    def test_running_cancelled_and_unavailable_required_checks_block_readiness(self) -> None:
        future = make_future()
        assurance_set = RequiredAssuranceSet("OVC-AA-TEST", "AA-PACKET-A", "v1", (future.future_id,))
        self.assertFalse(required_assurance_satisfied(assurance_set, {future.future_id: future}))
        cancelled = replace(future, state="CANCELLED", conclusion="cancelled")
        self.assertFalse(required_assurance_satisfied(assurance_set, {future.future_id: cancelled}))
        self.assertFalse(required_assurance_satisfied(assurance_set, {}))

    def test_correctable_parent_failure_selectively_invalidates_descendants(self) -> None:
        invalidated, preserved = selective_descendant_invalidation(
            [
                {"packet_id": "B", "dependency_ids": ["A"]},
                {"packet_id": "C", "dependency_ids": ["UNRELATED"]},
            ],
            ["A"],
        )
        self.assertEqual(invalidated, ("B",))
        self.assertEqual(preserved, ("C",))

    def test_blocking_failure_in_one_lane_does_not_stop_unrelated_running_lane(self) -> None:
        blocked = replace(make_future(), state="FAIL_BLOCKING", conclusion="failure")
        unrelated = make_future(packet_id="UNRELATED", payload_id="payload-u")
        self.assertFalse(should_continue_development(blocked))
        self.assertTrue(should_continue_development(unrelated))

    def test_operator_required_gate_parks_even_when_all_assurance_green(self) -> None:
        future = replace(make_future(), state="PASS", conclusion="success")
        assurance_set = RequiredAssuranceSet("OVC-AA-TEST", "AA-PACKET-A", "v1", (future.future_id,))
        parked, wake = evaluate_materialisation_intent(
            make_intent(assurance_set.assurance_set_id, operator_required=True),
            assurance_set,
            {future.future_id: future},
            readiness(),
        )
        self.assertEqual(parked.state, "WAITING_OPERATOR")
        self.assertIsNone(wake)

    def test_provider_adapter_has_negative_write_and_merge_reachability(self) -> None:
        capabilities = provider_capabilities()
        self.assertTrue(capabilities["read_only"])
        self.assertFalse(capabilities["repository_write"])
        self.assertFalse(capabilities["merge"])
        self.assertFalse(capabilities["force_push"])
        with self.assertRaises(ValueError):
            AssuranceWakeSubscription(
                GITHUB_PROVIDER_ADAPTER_ID,
                ("future",),
                ("intent",),
                controller_identity="NEW_AUTONOMOUS_WRITER",
            )

    def test_crash_after_green_before_lease_recovers_same_intent_without_phantom_completion(self) -> None:
        future = replace(make_future(), state="PASS", conclusion="success")
        assurance_set = RequiredAssuranceSet("OVC-AA-TEST", "AA-PACKET-A", "v1", (future.future_id,))
        intent = make_intent(assurance_set.assurance_set_id)
        with tempfile.TemporaryDirectory() as tmp:
            store = AsyncAssuranceStore(tmp)
            store.put_future(future)
            store.put_intent(intent)
            restored_future = store.get_future(future.future_id)
            restored_intent = store.get_intent(intent.intent_id)
            waiting, wake = evaluate_materialisation_intent(
                restored_intent,
                assurance_set,
                {restored_future.future_id: restored_future},
                readiness(LEASE_READY=False),
            )
            self.assertEqual(waiting.state, "WAITING_LEASE")
            self.assertIsNone(wake)

    def test_existing_pmt_recovery_handles_lease_before_write_crash(self) -> None:
        transaction = PhysicalMaterialisationTransaction(
            vit_generation_id="vit-a",
            ticket_id="ticket-a",
            train_generation_id="train-a",
            expected_predecessor_commit="base-commit",
            expected_predecessor_tree="base-tree",
            expected_result_tree="result-tree",
            authority_frontier_id="authority-a",
            assurance_frontier_id="assurance-a",
            materialisation_profile="LIVE_PHYSICAL_MAIN",
        )
        self.assertEqual(
            recover_unknown_write(transaction, "base-commit", "base-tree"),
            "WRITE_NOT_EFFECTIVE_RETRYABLE",
        )

    def test_main_movement_preserves_only_declared_aa0_reusable_evidence(self) -> None:
        reusable = replace(make_future(), state="PASS", conclusion="success")
        self.assertEqual(reuse_after_frontier_change(reusable, {"physical_main"}).state, "PASS")
        edge = replace(
            reusable,
            assurance_class=AA2_MATERIALISATION_EDGE,
            reuse_class=NO_REUSE,
            dependency_scope=("physical_main",),
        )
        self.assertEqual(reuse_after_frontier_change(edge, {"physical_main"}).state, "STALE")

    def test_exact_predecessor_materialisation_promotes_speculative_successor_without_rebuild(self) -> None:
        self.assertEqual(
            promote_speculative_successor(
                "SPECULATIVE_RUNNING",
                expected_predecessor_tree="tree-a",
                observed_predecessor_tree="tree-a",
                dependencies_valid=True,
            ),
            "AUTHORITATIVE_RUNNING",
        )

    def test_unknown_assurance_classification_defaults_to_aa2_no_reuse(self) -> None:
        future = make_future(assurance_class="UNKNOWN", reuse_class="UNKNOWN")
        self.assertEqual(future.assurance_class, AA2_MATERIALISATION_EDGE)
        self.assertEqual(future.reuse_class, NO_REUSE)

    def test_speculative_irreversible_side_effect_barrier(self) -> None:
        self.assertFalse(speculative_action_allowed("PUBLICATION", predecessor_authoritative=False))
        self.assertFalse(speculative_action_allowed("PROVIDER_INTAKE", predecessor_authoritative=False))
        self.assertTrue(speculative_action_allowed("LOCAL_BUILD", predecessor_authoritative=False))

    def test_complete_green_set_only_wakes_existing_controller_and_does_not_merge(self) -> None:
        future = replace(make_future(), state="PASS", conclusion="success")
        assurance_set = RequiredAssuranceSet("OVC-AA-TEST", "AA-PACKET-A", "v1", (future.future_id,))
        ready, wake = evaluate_materialisation_intent(
            make_intent(assurance_set.assurance_set_id),
            assurance_set,
            {future.future_id: future},
            readiness(),
        )
        self.assertEqual(ready.state, "MATERIALISATION_READY")
        assert wake is not None
        self.assertEqual(wake.controller_identity, CONTROLLER_IDENTITY)
        self.assertEqual(wake.action, "REQUEST_SERIALIZED_SQUASH_MATERIALISATION")
        self.assertEqual(wake.authority_effect, "NONE")

    def test_repository_profile_is_explicit_and_schemas_are_machine_readable(self) -> None:
        profile = json.loads((ROOT / "registries/development/skills/async_assurance/REQUIRED_ASSURANCE_PROFILE_v0_1.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["classification_rule"], "EXPLICIT_ONLY_NEVER_INFER_FROM_WORKFLOW_NAME")
        self.assertFalse(profile["provider_write_or_merge_capability"])
        self.assertEqual(profile["controller_identity"], CONTROLLER_IDENTITY)
        for member in profile["members"]:
            self.assertIn(member["assurance_class"], {"AA0_BACKGROUND_REUSABLE", "AA2_MATERIALISATION_EDGE"})
            self.assertIn(member["reuse_class"], {"REUSE_IF_DEPENDENCIES_UNCHANGED", "NO_REUSE"})
            self.assertTrue(member["dependency_scope"])
        schema_root = ROOT / "schemas/development/async_assurance"
        for name in (
            "assurance_future_v1.schema.json",
            "assurance_completion_signal_v1.schema.json",
            "required_assurance_set_v1.schema.json",
            "conditional_materialisation_intent_v1.schema.json",
            "assurance_wake_subscription_v1.schema.json",
        ):
            self.assertIsInstance(json.loads((schema_root / name).read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
