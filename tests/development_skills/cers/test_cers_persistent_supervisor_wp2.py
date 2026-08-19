from __future__ import annotations

import unittest

from ovc.development.skills.cers.persistent import (
    PersistentWorkRequest,
    derive_authority_view,
    reconcile_persistent_requests,
    route_failure_to_owner,
)


PROGRAMME = "OVC-TEST-PROGRAMME-v1"
ROOT = "registries/implementation/test/CURRENT_STATE_POINTER.json"
PLAN = "OVC-TEST-PLAN-v1"
BINDING = "OVC-CERS-PERSISTENT-EXECUTOR-BINDING-v0.1"
EXECUTOR = "OVC-SKILL-030@0.1.0+sha256:fixture|PACKET_EXECUTION|windows-local-python311"


def policy():
    return {
        "allowed_authority_classes": ["AUTO_EXECUTABLE", "AUTO_RATIFIABLE"],
        "future_programme_auto_admission": False,
        "direct_main_mutation": False,
        "merge_capability": "NONE",
        "parallel_physical_merge": False,
        "force_push": False,
        "history_rewrite": False,
        "irreversible_external_side_effects": False,
    }


def admission(programme_id=PROGRAMME):
    return {
        "status": "ACTIVE",
        "programme_id": programme_id,
        "current_state_root": ROOT,
        "governing_plan_id": PLAN,
        "owner_authority_source": "records/test/AUTHORITY.json",
        "eligible_authority_classes": ["AUTO_EXECUTABLE", "AUTO_RATIFIABLE"],
        "eligible_packet_classes": ["LOW_RISK_IMPLEMENTATION"],
        "allowed_side_effect_classes": ["BRANCH_REVERSIBLE", "READ_ONLY"],
        "executor_binding_id": BINDING,
        "write_domain_rule": "PACKET_DECLARED_WRITE_DOMAIN_AND_SEMANTIC_OWNER_ONLY",
        "semantic_owner_rule": "EXACT_PACKET_SEMANTIC_OWNER_ONLY",
        "operator_boundary_policy": "PARK",
        "explicit_prohibitions": ["MERGE", "DIRECT_MAIN_WRITE", "FORCE_PUSH", "HISTORY_REWRITE"],
    }


def executor():
    return {
        "binding_id": BINDING,
        "status": "ACTIVE",
        "executor_identity": EXECUTOR,
        "action_classes": ["WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"],
        "merge": False,
        "force_push": False,
        "history_rewrite": False,
        "irreversible_external_side_effects": False,
    }


def action_registry():
    return {
        "entries": [
            {"action": "WRITE_FILE", "side_effect_class": "BRANCH_REVERSIBLE", "allowed": True},
            {"action": "GIT_COMMIT", "side_effect_class": "BRANCH_REVERSIBLE", "allowed": True},
            {"action": "PUSH_BRANCH", "side_effect_class": "BRANCH_REVERSIBLE", "allowed": True},
        ],
        "explicit_denies": ["MERGE", "DIRECT_MAIN_WRITE", "FORCE_PUSH", "HISTORY_REWRITE", "VALIDATION_READ", "SCIENTIFIC_PROMOTION", "CANONICAL_PUBLICATION", "R2_PUBLICATION", "PROBABILITY", "RISK", "EXPOSURE", "TRADING", "MARKET_EXECUTION"],
    }


def request(*, programme_id=PROGRAMME, packet_id="WP1", action="WRITE_FILE", authority_required="AUTO_EXECUTABLE", operator_boundary=False, priority=100, side_effect_class="BRANCH_REVERSIBLE", root=ROOT, prerequisites_pass=True, dependency_frontier_current=True, write_domain="src/test/", semantic_owner="OVC-TEST"):
    return PersistentWorkRequest(
        programme_id=programme_id,
        current_state_root=root,
        governing_plan_id=PLAN,
        packet_id=packet_id,
        packet_class="LOW_RISK_IMPLEMENTATION",
        authority_class="AUTO_EXECUTABLE",
        authority_required=authority_required,
        owner_authority_source="records/test/AUTHORITY.json",
        owner_authority_current=True,
        executor_binding_id=BINDING,
        action=action,
        side_effect_class=side_effect_class,
        write_domain=write_domain,
        semantic_owner=semantic_owner,
        write_domain_declared=write_domain is not None,
        semantic_owner_match=semantic_owner == "OVC-TEST",
        prerequisites_pass=prerequisites_pass,
        dependency_frontier_current=dependency_frontier_current,
        operator_boundary=operator_boundary,
        priority=priority,
    )


class PersistentSupervisorWp2Tests(unittest.TestCase):
    def test_exact_active_admission_can_be_derived_without_granting_authority(self):
        r = request()
        v = derive_authority_view(
            r,
            admission=admission(),
            policy=policy(),
            executor_binding=executor(),
            action_registry=action_registry(),
            quiescence_mode="RUN",
        )
        self.assertEqual(v.decision, "ALLOW")
        self.assertEqual(v.primary_reason, "RUNNABLE")
        self.assertEqual(v.authority_effect, "NONE")

    def test_missing_or_stale_admission_fails_closed(self):
        r = request()
        missing = derive_authority_view(r, admission=None, policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="RUN")
        self.assertEqual((missing.decision, missing.primary_reason), ("DENY", "PROGRAMME_NOT_ADMITTED"))
        stale = derive_authority_view(request(root="registries/implementation/test/OLD.json"), admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="RUN")
        self.assertEqual((stale.decision, stale.primary_reason), ("DENY", "PROGRAMME_ROOT_STALE"))

    def test_operator_boundary_parks_without_blocking_unrelated_admitted_work(self):
        blocked = request(packet_id="G-OPERATOR", authority_required="OPERATOR_REQUIRED", operator_boundary=True, priority=1)
        runnable = request(packet_id="WP-NEXT", priority=2)
        result = reconcile_persistent_requests(
            [runnable, blocked],
            snapshot_id="snapshot-1",
            admissions={PROGRAMME: admission()},
            policy=policy(),
            executor_bindings={BINDING: executor()},
            action_registry=action_registry(),
            quiescence_mode="RUN",
            fencing_generation=7,
        )
        by_packet = {view.packet_id: view for view in result.views}
        self.assertEqual(by_packet["G-OPERATOR"].decision, "PARK")
        self.assertEqual(by_packet["G-OPERATOR"].primary_reason, "OPERATOR_REQUIRED_BOUNDARY")
        self.assertEqual(by_packet["WP-NEXT"].decision, "ALLOW")
        self.assertEqual([d.packet_id for d in result.dispatches], ["WP-NEXT"])

    def test_deterministic_input_order_and_content_addressed_dispatch(self):
        a = request(packet_id="WP-A", priority=20)
        b = request(packet_id="WP-B", priority=10)
        kwargs = dict(
            snapshot_id="snapshot-fixed",
            admissions={PROGRAMME: admission()},
            policy=policy(),
            executor_bindings={BINDING: executor()},
            action_registry=action_registry(),
            quiescence_mode="RUN",
            fencing_generation=3,
        )
        one = reconcile_persistent_requests([a, b], **kwargs)
        two = reconcile_persistent_requests([b, a], **kwargs)
        self.assertEqual(one.result_id, two.result_id)
        self.assertEqual([v.packet_id for v in one.views], ["WP-B", "WP-A"])
        self.assertEqual([d.dispatch_id for d in one.dispatches], [d.dispatch_id for d in two.dispatches])

    def test_quiescence_parks_new_work(self):
        r = request()
        v = derive_authority_view(r, admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="DISABLE_NEW_DISPATCH")
        self.assertEqual((v.decision, v.primary_reason), ("PARK", "QUIESCENCE_DISABLE_NEW_DISPATCH"))

    def test_hard_deny_precedes_quiescence(self):
        r = request(side_effect_class="IRREVERSIBLE_OR_UNKNOWN")
        v = derive_authority_view(r, admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="HOLD")
        self.assertEqual(v.decision, "DENY")
        self.assertEqual(v.primary_reason, "SIDE_EFFECT_UNKNOWN_OR_DENIED")

    def test_write_domain_and_semantic_owner_are_exact(self):
        no_domain = request(write_domain=None)
        v = derive_authority_view(no_domain, admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="RUN")
        self.assertEqual((v.decision, v.primary_reason), ("DENY", "WRITE_DOMAIN_UNKNOWN_OR_DENIED"))
        wrong_owner = request(semantic_owner="OTHER")
        v = derive_authority_view(wrong_owner, admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="RUN")
        self.assertEqual((v.decision, v.primary_reason), ("DENY", "SEMANTIC_OWNER_MISMATCH"))

    def test_reserved_action_and_unknown_action_never_dispatch(self):
        reserved = request(action="MERGE")
        v = derive_authority_view(reserved, admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="RUN")
        self.assertEqual((v.decision, v.primary_reason), ("DENY", "ACTION_EXPLICITLY_DENIED"))
        unknown = request(action="SOMETHING_NEW")
        v = derive_authority_view(unknown, admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="RUN")
        self.assertEqual((v.decision, v.primary_reason), ("DENY", "ACTION_UNKNOWN_OR_DENIED"))

    def test_stale_dependency_parks_and_failure_routes_to_owner(self):
        r = request(dependency_frontier_current=False)
        v = derive_authority_view(r, admission=admission(), policy=policy(), executor_binding=executor(), action_registry=action_registry(), quiescence_mode="RUN")
        self.assertEqual((v.decision, v.primary_reason), ("PARK", "DEPENDENCY_FRONTIER_STALE"))
        route = route_failure_to_owner(PROGRAMME, "WP1", "FIXTURE_FAILURE")
        self.assertEqual(route["route"], "EXISTING_PROGRAMME_REPAIR_OWNER")
        self.assertEqual(route["cers_remediation_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
