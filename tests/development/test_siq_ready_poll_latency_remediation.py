from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
from dataclasses import asdict
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_late_binding import BaseIndependentAssuranceGeneration
import tools.ci.prvitr_live_admission as live


ROOT = Path(__file__).resolve().parents[2]
HEAD = "9" * 40
TREE = "8" * 40
PIP = "7" * 64
AUTHORITY = "6" * 64
FRONTIER = "5" * 64
QUALIFICATION = "4" * 64
PR_NUMBER = 1391
PACKET_DIR = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/siq-ready-poll-latency-remediation"


def workflow_run(
    run_id: int,
    *,
    head: str = HEAD,
    pr: int = PR_NUMBER,
    number: int = 1,
    attempt: int = 1,
) -> dict:
    return {
        "id": run_id,
        "head_sha": head,
        "pull_requests": [{"number": pr}],
        "run_number": number,
        "run_attempt": attempt,
    }


def job(name: str, *, job_id: int, status: str = "completed", conclusion: str = "success", attempt: int = 1) -> dict:
    return {
        "id": job_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "run_attempt": attempt,
    }


def successful_test_jobs() -> list[dict]:
    return [job(name, job_id=100 + index) for index, name in enumerate(live.TEST_JOB_NAMES)]


def reference_old_wait_state_evaluator(jobs: list[dict], required_names: tuple[str, ...]) -> tuple[str, tuple[dict, ...]]:
    selected: list[dict] = []
    for name in required_names:
        matches = [row for row in jobs if row.get("name") == name]
        if not matches:
            return "PENDING", tuple(selected)
        current = sorted(matches, key=lambda row: int(row.get("id", 0)), reverse=True)[0]
        selected.append(current)
        if current.get("status") == "completed" and current.get("conclusion") != "success":
            return "FAIL", tuple(selected)
        if current.get("status") != "completed":
            return "PENDING", tuple(selected)
    return "PASS", tuple(selected)


class FakeClock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class SIQReadyStateEvaluationTests(unittest.TestCase):
    def test_equivalence_corpus_decision_equality_is_100_percent(self) -> None:
        passed = successful_test_jobs()
        corpus = {
            "PASS": passed,
            "PENDING_RUNNING": [*passed[:-1], job(live.TEST_JOB_NAMES[-1], job_id=999, status="in_progress", conclusion="")],
            "FAIL": [*passed[:-1], job(live.TEST_JOB_NAMES[-1], job_id=999, conclusion="failure")],
            "MISSING_JOB": passed[:-1],
            "DUPLICATE_JOB": [*passed, job(live.TEST_JOB_NAMES[-1], job_id=50, conclusion="failure")],
        }
        equal = 0
        for name, rows in corpus.items():
            with self.subTest(name=name):
                reference = reference_old_wait_state_evaluator(rows, live.TEST_JOB_NAMES)
                candidate = live.evaluate_required_jobs(rows, live.TEST_JOB_NAMES)
                self.assertEqual(candidate, reference)
                equal += int(candidate == reference)
        self.assertEqual(equal, len(corpus))

    def test_wrong_head_run_rejected(self) -> None:
        self.assertIsNone(live._select_exact_run([workflow_run(1, head="a" * 40)], PR_NUMBER, HEAD))

    def test_wrong_pr_run_rejected(self) -> None:
        self.assertIsNone(live._select_exact_run([workflow_run(1, pr=PR_NUMBER + 1)], PR_NUMBER, HEAD))

    def test_newer_run_attempt_selected_over_older_exact_run(self) -> None:
        older = workflow_run(10, number=4, attempt=1)
        newer = workflow_run(10, number=4, attempt=2)
        self.assertIs(live._select_exact_run([older, newer], PR_NUMBER, HEAD), newer)

    def test_newer_run_number_selected_over_larger_old_id(self) -> None:
        old = workflow_run(999, number=3)
        current = workflow_run(100, number=4)
        self.assertIs(live._select_exact_run([old, current], PR_NUMBER, HEAD), current)

    def test_required_tests_job_absent_is_pending(self) -> None:
        state, _ = live.evaluate_required_jobs(successful_test_jobs()[:-1], live.TEST_JOB_NAMES)
        self.assertEqual(state, "PENDING")

    def test_required_profile_job_absent_is_pending(self) -> None:
        state, _ = live.evaluate_required_jobs([], (live.PROFILE_JOB_NAME,))
        self.assertEqual(state, "PENDING")

    def test_required_job_running_is_pending(self) -> None:
        state, _ = live.evaluate_required_jobs(
            [job(live.PROFILE_JOB_NAME, job_id=1, status="in_progress", conclusion="")],
            (live.PROFILE_JOB_NAME,),
        )
        self.assertEqual(state, "PENDING")

    def test_required_job_failure_is_fail(self) -> None:
        state, _ = live.evaluate_required_jobs(
            [job(live.PROFILE_JOB_NAME, job_id=1, conclusion="cancelled")],
            (live.PROFILE_JOB_NAME,),
        )
        self.assertEqual(state, "FAIL")

    def test_all_required_jobs_success_is_pass(self) -> None:
        state, selected = live.evaluate_required_jobs(successful_test_jobs(), live.TEST_JOB_NAMES)
        self.assertEqual(state, "PASS")
        self.assertEqual(tuple(row["name"] for row in selected), live.TEST_JOB_NAMES)

    def test_changed_run_attempt_fails_closed(self) -> None:
        state, _ = live.evaluate_required_jobs(
            [job(live.PROFILE_JOB_NAME, job_id=1, attempt=2)],
            (live.PROFILE_JOB_NAME,),
            expected_run_attempt=1,
        )
        self.assertEqual(state, "FAIL")

    def test_pr1391_payload_replays_with_identical_pass_and_evidence_set(self) -> None:
        rows = [
            job("VIT routing preflight", job_id=98700800064),
            job("tests", job_id=98700872443),
            job("pytest-unittest-parity", job_id=98700836843),
            job("runner-parity", job_id=98700836861),
        ]
        reference = reference_old_wait_state_evaluator(rows, live.TEST_JOB_NAMES)
        candidate = live.evaluate_required_jobs(rows, live.TEST_JOB_NAMES, expected_run_attempt=1)
        self.assertEqual(candidate, reference)
        self.assertEqual(candidate[0], "PASS")
        self.assertEqual(
            tuple(row["id"] for row in candidate[1]),
            (98700800064, 98700872443, 98700836843, 98700836861),
        )


class SIQReadyWaitTests(unittest.TestCase):
    def _runs(self) -> tuple[dict, dict]:
        return workflow_run(10), workflow_run(20)

    def test_exact_runs_discovered_once_and_pinned(self) -> None:
        clock = FakeClock()
        tests_run, tiered_run = self._runs()
        diagnostics = live.AssurancePollDiagnostics()
        exact_calls: list[str] = []

        def exact(workflow: str, _pr: int, _head: str) -> dict:
            exact_calls.append(workflow)
            return tests_run if workflow == live.TESTS_WORKFLOW else tiered_run

        def jobs(run_id: int) -> list[dict]:
            if run_id == 10:
                rows = successful_test_jobs()
                if clock.value < 4:
                    rows[-1] = job(live.TEST_JOB_NAMES[-1], job_id=999, status="in_progress", conclusion="")
                return rows
            return [job(live.PROFILE_JOB_NAME, job_id=200)]

        with patch.object(live, "_exact_run", side_effect=exact), patch.object(live, "_jobs", side_effect=jobs):
            result = live.wait_exact_assurance(
                PR_NUMBER,
                HEAD,
                now=clock.now,
                sleep=clock.sleep,
                diagnostics=diagnostics,
            )
        self.assertEqual(result[0]["id"], 10)
        self.assertEqual(result[2]["id"], 20)
        self.assertEqual(exact_calls, [live.TESTS_WORKFLOW, live.TIERED_WORKFLOW])
        self.assertEqual(diagnostics.discovery_api_operations, 2)
        self.assertEqual(diagnostics.active_cycles, 3)
        self.assertEqual(diagnostics.active_api_operations, 6)
        self.assertEqual(clock.sleeps, [2.0, 2.0])

    def test_missing_workflow_uses_bounded_discovery_polling(self) -> None:
        clock = FakeClock()
        diagnostics = live.AssurancePollDiagnostics()
        with patch.object(live, "_exact_run", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "SIQ_READY_ADMISSION_TIMEOUT"):
                live.wait_exact_assurance(
                    PR_NUMBER,
                    HEAD,
                    timeout_seconds=5,
                    now=clock.now,
                    sleep=clock.sleep,
                    diagnostics=diagnostics,
                )
        self.assertEqual(clock.sleeps, [2.0, 2.0, 1.0])
        self.assertEqual(clock.value, 5.0)

    def test_failure_returns_immediately_without_profile_fetch_or_sleep(self) -> None:
        clock = FakeClock()
        tests_run, tiered_run = self._runs()

        def exact(workflow: str, _pr: int, _head: str) -> dict:
            return tests_run if workflow == live.TESTS_WORKFLOW else tiered_run

        failed = successful_test_jobs()
        failed[0] = job(live.TEST_JOB_NAMES[0], job_id=100, conclusion="failure")
        with patch.object(live, "_exact_run", side_effect=exact), patch.object(live, "_jobs", return_value=failed) as fetch:
            with self.assertRaisesRegex(RuntimeError, "SIQ_EXACT_TESTS_WORKFLOW_FAILED"):
                live.wait_exact_assurance(PR_NUMBER, HEAD, now=clock.now, sleep=clock.sleep)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(clock.sleeps, [])

    def test_final_pass_has_no_additional_fixed_delay(self) -> None:
        clock = FakeClock()
        tests_run, tiered_run = self._runs()

        def exact(workflow: str, _pr: int, _head: str) -> dict:
            return tests_run if workflow == live.TESTS_WORKFLOW else tiered_run

        def jobs(run_id: int) -> list[dict]:
            return successful_test_jobs() if run_id == 10 else [job(live.PROFILE_JOB_NAME, job_id=200)]

        with patch.object(live, "_exact_run", side_effect=exact), patch.object(live, "_jobs", side_effect=jobs):
            live.wait_exact_assurance(PR_NUMBER, HEAD, now=clock.now, sleep=clock.sleep)
        self.assertEqual(clock.value, 0.0)
        self.assertEqual(clock.sleeps, [])

    def test_polling_cadence_is_bounded_configurable_and_validated(self) -> None:
        for discovery, active in ((0, 2), (2, 0), (-1, 2), (2, -1)):
            with self.subTest(discovery=discovery, active=active):
                with self.assertRaisesRegex(ValueError, "SIQ_READY_POLL_CONFIGURATION_INVALID"):
                    live.wait_exact_assurance(
                        PR_NUMBER,
                        HEAD,
                        discovery_poll_seconds=discovery,
                        active_poll_seconds=active,
                    )

    def test_ready_timeout_remains_unchanged(self) -> None:
        self.assertEqual(live.READY_TIMEOUT_SECONDS, 22 * 60)

    def test_fake_clock_detects_transition_within_two_seconds(self) -> None:
        clock = FakeClock(26.084761)
        tests_run, tiered_run = self._runs()

        def exact(workflow: str, _pr: int, _head: str) -> dict:
            return tests_run if workflow == live.TESTS_WORKFLOW else tiered_run

        def jobs(run_id: int) -> list[dict]:
            if run_id == 20:
                return [job(live.PROFILE_JOB_NAME, job_id=200)]
            rows = successful_test_jobs()
            if clock.value < 33.0:
                rows[1] = job("tests", job_id=101, status="in_progress", conclusion="")
            return rows

        with patch.object(live, "_exact_run", side_effect=exact), patch.object(live, "_jobs", side_effect=jobs):
            live.wait_exact_assurance(PR_NUMBER, HEAD, now=clock.now, sleep=clock.sleep)
        self.assertAlmostEqual(clock.value, 34.084761)
        self.assertLessEqual(clock.value - 33.0, 2.0)

    def test_pr1391_reference_and_candidate_detection_replay(self) -> None:
        waiter_started = 26.084761
        final_aa0_ready = 33.0
        old_detection = waiter_started + math.ceil((final_aa0_ready - waiter_started) / 10.0) * 10.0
        candidate_detection = waiter_started + math.ceil((final_aa0_ready - waiter_started) / 2.0) * 2.0
        self.assertAlmostEqual(old_detection, 36.084761)
        self.assertAlmostEqual(candidate_detection, 34.084761)
        self.assertAlmostEqual(old_detection - candidate_detection, 2.0)
        self.assertLessEqual(candidate_detection - final_aa0_ready, 2.0)


class SIQReadyLiveRevalidationTests(unittest.TestCase):
    def _context(self, *, pip: str = PIP, authority: str = AUTHORITY, frontier: str = FRONTIER, qualification: str = QUALIFICATION) -> tuple:
        return {}, SimpleNamespace(pip_id=pip, late_binding=True), authority, frontier, qualification

    def _execute_ready(self, *, refreshed_head: str = HEAD, refreshed_context: tuple | None = None) -> str:
        initial_pr = {"state": "open", "head": {"sha": HEAD}, "body": ""}
        refreshed_pr = {"state": "open", "head": {"sha": refreshed_head}, "body": ""}
        tests_run = workflow_run(10)
        tiered_run = workflow_run(20)
        test_jobs = tuple(successful_test_jobs())
        profile = job(live.PROFILE_JOB_NAME, job_id=200)
        output = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch.object(live, "_event", return_value={"number": PR_NUMBER, "pull_request": {"head": {"sha": HEAD}}}))
            stack.enter_context(patch.object(live, "_live_pr", side_effect=[initial_pr, refreshed_pr]))
            stack.enter_context(patch.object(live, "_payload_context", side_effect=[self._context(), refreshed_context or self._context()]))
            stack.enter_context(patch.object(live, "_wait_exact_assurance", return_value=(tests_run, test_jobs, tiered_run, profile)))
            stack.enter_context(patch.object(live, "_tree", return_value=TREE))
            stack.enter_context(patch.object(live, "_write_output"))
            stack.enter_context(redirect_stdout(output))
            live.command_ready()
        return output.getvalue()

    def test_live_pr_head_revalidated_after_pass(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "OVC_SIQ_SUPERSEDED_EVENT_HEAD"):
            self._execute_ready(refreshed_head="a" * 40)

    def test_qualification_change_after_assurance_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_CHANGED_DURING_ASSURANCE"):
            self._execute_ready(refreshed_context=self._context(qualification="a" * 64))

    def test_pip_change_after_assurance_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_CONTENT_CHANGED_DURING_ASSURANCE"):
            self._execute_ready(refreshed_context=self._context(pip="a" * 64))

    def test_authority_manifest_change_after_assurance_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_CONTENT_CHANGED_DURING_ASSURANCE"):
            self._execute_ready(refreshed_context=self._context(authority="a" * 64))

    def test_dependency_frontier_change_after_assurance_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "VIT_QUALIFICATION_CONTENT_CHANGED_DURING_ASSURANCE"):
            self._execute_ready(refreshed_context=self._context(frontier="a" * 64))

    def test_exact_source_run_ids_remain_identical_in_meaning(self) -> None:
        output = self._execute_ready()
        line = next(row for row in output.splitlines() if row.startswith("OVC_BASE_INDEPENDENT_ASSURANCE_GENERATION="))
        generation = json.loads(line.split("=", 1)[1])
        self.assertEqual(
            generation["source_run_ids"],
            [
                "github-actions-run:10:job:100",
                "github-actions-run:10:job:101",
                "github-actions-run:10:job:102",
                "github-actions-run:10:job:103",
                "github-actions-run:20:job:200",
            ],
        )

    def test_base_independent_generation_schema_identity_unchanged(self) -> None:
        generation = BaseIndependentAssuranceGeneration(
            pip_id=PIP,
            candidate_head_sha=HEAD,
            candidate_head_tree=TREE,
            authority_manifest_id=AUTHORITY,
            dependency_frontier_id=FRONTIER,
            policy_id=live.POLICY_ID,
            source_run_ids=("github-actions-run:10:job:100",),
        )
        self.assertEqual(
            set(asdict(generation)),
            {
                "pip_id",
                "candidate_head_sha",
                "candidate_head_tree",
                "authority_manifest_id",
                "dependency_frontier_id",
                "policy_id",
                "source_run_ids",
            },
        )


class SIQReadyContractPreservationTests(unittest.TestCase):
    def test_required_evidence_set_is_unchanged(self) -> None:
        self.assertEqual(
            live.TEST_JOB_NAMES,
            ("VIT routing preflight", "tests", "pytest-unittest-parity", "runner-parity"),
        )
        self.assertEqual(live.PROFILE_JOB_NAME, "OVC profile assurance")

    def test_no_unconditional_ten_second_sleep_remains_on_ready_paths(self) -> None:
        admission = (ROOT / "tools/ci/prvitr_live_admission.py").read_text(encoding="utf-8")
        selector = (ROOT / "tools/ci/prvitr_rac_ready.py").read_text(encoding="utf-8")
        self.assertNotIn("time.sleep(10)", admission)
        self.assertNotIn("time.sleep(10)", selector)

    def test_workflow_and_one_writer_final_materialisation_semantics_unchanged(self) -> None:
        tiered = (ROOT / ".github/workflows/ovc-tiered-tests.yml").read_text(encoding="utf-8")
        tests = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertIn("needs: [profile, siq-ready-admission]", tiered)
        self.assertIn("group: ovc-main-integration-lane-v1", tiered)
        self.assertIn("Acquire one-writer lease and late-bind current physical main", tiered)
        self.assertIn("Run mandatory SIQ/PDC exact-final assurance inside lease", tiered)
        self.assertIn("OVC merge readiness", tests)

    def test_rac_fallback_and_reference_behavior_unchanged(self) -> None:
        selector = (ROOT / "tools/ci/prvitr_rac_ready.py").read_text(encoding="utf-8")
        self.assertIn("FALLBACK_CANONICAL_REFERENCE", selector)
        self.assertIn("return live.command_ready()", selector)
        self.assertIn("OVC_RAC_PILOT_CANONICAL_REFERENCE=CONCURRENT_NOT_READY_BLOCKING", selector)

    def test_packet_artifacts_are_authority_none_and_record_successor_obligation(self) -> None:
        manifest = json.loads((PACKET_DIR / "DSAI3V_SIQ_READY_POLL_LATENCY_AUTHORITY_MANIFEST_v0_1.json").read_text(encoding="utf-8"))
        frontier = json.loads((PACKET_DIR / "DSAI3V_SIQ_READY_POLL_LATENCY_DEPENDENCY_FRONTIER_v0_1.json").read_text(encoding="utf-8"))
        packet = json.loads((PACKET_DIR / "DSAI3V_SIQ_READY_POLL_LATENCY_REMEDIATION_PACKET_v0_1.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["authority_delta"], "NONE")
        self.assertEqual(manifest["logical_id"], canonical_sha256({k: v for k, v in manifest.items() if k != "logical_id"}))
        self.assertEqual(frontier["logical_id"], canonical_sha256({k: v for k, v in frontier.items() if k != "logical_id"}))
        self.assertEqual(packet["classification_on_success"], "SIQ_READY_POLL_LATENCY_REMEDIATION_PASS")
        self.assertEqual(packet["standing_validation_requirement"], "NEXT_ELIGIBLE_AA0_PREWARM_PACKET")
        self.assertFalse(packet["production_sub60_claim_permitted"])


if __name__ == "__main__":
    unittest.main()
