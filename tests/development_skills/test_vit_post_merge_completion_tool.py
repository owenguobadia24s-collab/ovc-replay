from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request


TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "ci" / "vit_post_merge_completion.py"
SPEC = importlib.util.spec_from_file_location("vit_post_merge_completion_tool", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class _Response:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._body


class _Opener:
    def __init__(self, body: bytes = b"job-log"):
        self.body = body
        self.requests = []

    def open(self, request, timeout=30):
        self.requests.append(request)
        return _Response(self.body)


class VitPostMergeCompletionToolTests(unittest.TestCase):
    def test_request_uses_supported_github_media_type(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["accept"] = request.get_header("Accept")
            captured["authorization"] = request.get_header("Authorization")
            captured["url"] = request.full_url
            return _Response(b"{}")

        with patch.object(TOOL, "urlopen", side_effect=fake_urlopen):
            body = TOOL._request("https://api.github.com/repos/o/r", "token")

        self.assertEqual(captured["accept"], "application/vnd.github+json")
        self.assertEqual(captured["authorization"], "Bearer token")
        self.assertEqual(captured["url"], "https://api.github.com/repos/o/r")
        self.assertEqual(body, b"{}")

    def test_job_log_request_authenticates_api_request(self) -> None:
        opener = _Opener(b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=abc")
        with patch.object(TOOL, "build_opener", return_value=opener) as factory:
            body = TOOL._request_job_log(
                "https://api.github.com/repos/o/r/actions/jobs/123/logs", "token"
            )
        factory.assert_called_once()
        self.assertEqual(len(opener.requests), 1)
        request = opener.requests[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer token")
        self.assertEqual(request.get_header("Accept"), "application/vnd.github+json")
        self.assertTrue(request.full_url.endswith("/actions/jobs/123/logs"))
        self.assertIn(b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64", body)

    def test_job_log_redirect_strips_authorization_but_preserves_media_type(self) -> None:
        handler = TOOL._StripAuthorizationOnRedirect()
        request = Request(
            "https://api.github.com/repos/o/r/actions/jobs/123/logs",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer token",
                "User-Agent": "ovc-vit-local-post-merge-completion/v2",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://signed-log-storage.example/job-log",
        )
        self.assertIsNotNone(redirected)
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertEqual(redirected.get_header("Accept"), "application/vnd.github+json")
        self.assertEqual(redirected.full_url, "https://signed-log-storage.example/job-log")

    def test_non_log_request_remains_fail_closed_on_401(self) -> None:
        calls = []

        def fake_urlopen(request, timeout=30):
            calls.append(request)
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

        with patch.object(TOOL, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(TOOL.PostMergeCompletionError):
                TOOL._request("https://api.github.com/repos/o/r", "token")
        self.assertEqual(len(calls), 1)

    def test_freeze_lookup_prefers_late_merge_readiness_job(self) -> None:
        freeze = {"pr_number": 42, "head_sha": "f" * 40, "transaction": {}}
        calls = []

        def fake_json(url, token):
            if "/actions/runs?" in url:
                return {
                    "workflow_runs": [
                        {
                            "id": 9002,
                            "name": "OVC tiered test selection shadow",
                            "conclusion": "success",
                        },
                        {"id": 9001, "name": "tests", "conclusion": "success"},
                    ]
                }
            if "/actions/runs/9002/jobs" in url:
                return {
                    "jobs": [
                        {
                            "id": 8002,
                            "name": "OVC merge readiness",
                            "conclusion": "success",
                        }
                    ]
                }
            raise AssertionError(url)

        def fake_job_log(url, token):
            calls.append(url)
            return b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=payload"

        with (
            patch.object(TOOL, "_json", side_effect=fake_json),
            patch.object(TOOL, "_request_job_log", side_effect=fake_job_log),
            patch.object(TOOL, "decode_freeze_marker", return_value=freeze),
        ):
            observed = TOOL._freeze_from_physical_lane_logs(
                repository="o/r",
                head_sha="f" * 40,
                pr_number=42,
                token="token",
            )
        self.assertEqual(observed, freeze)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].endswith("/actions/jobs/8002/logs"))

    def test_historical_routing_preflight_is_fallback_only(self) -> None:
        freeze = {"pr_number": 42, "head_sha": "f" * 40, "transaction": {}}

        def fake_json(url, token):
            if "/actions/runs?" in url:
                return {
                    "workflow_runs": [
                        {"id": 9001, "name": "tests", "conclusion": "success"}
                    ]
                }
            if "/actions/runs/9001/jobs" in url:
                return {
                    "jobs": [
                        {
                            "id": 8001,
                            "name": "VIT routing preflight",
                            "conclusion": "success",
                        }
                    ]
                }
            raise AssertionError(url)

        log = b"2026-08-17T10:48:28Z OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=payload\n"
        with (
            patch.object(TOOL, "_json", side_effect=fake_json),
            patch.object(TOOL, "_request_job_log", return_value=log),
            patch.object(TOOL, "decode_freeze_marker", return_value=freeze) as decode,
        ):
            observed = TOOL._freeze_from_physical_lane_logs(
                repository="o/r", head_sha="f" * 40, pr_number=42, token="token"
            )
        self.assertEqual(observed, freeze)
        decode.assert_called_once_with("OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=payload")

    def test_frontier_ledger_envelope_is_revalidated_and_persisted_as_four_records(self) -> None:
        freeze = {"frontier_ledger_envelope": {"schema": "ovc-vit-frontier-ledger-envelope/v1"}}
        decoded = {
            "frontier_lineage": {"schema": "lineage"},
            "frontier_lineage_record_id": "1" * 64,
            "assurance_generation": {"schema": "assurance"},
            "assurance_generation_id": "2" * 64,
            "a2_proof": {"schema": "a2"},
            "a2_proof_id": "3" * 64,
            "envelope_record": {"schema": "envelope"},
            "envelope_record_id": "4" * 64,
        }

        class Store:
            def __init__(self):
                self.rows = []

            def put_record(self, record, record_id):
                self.rows.append((record, record_id))

        store = Store()
        with patch.object(TOOL, "validate_frontier_ledger_envelope", return_value=decoded) as validate:
            ids = TOOL._persist_frontier_ledger(freeze=freeze, receipt_store=store)
        validate.assert_called_once_with(freeze["frontier_ledger_envelope"])
        self.assertEqual([row[1] for row in store.rows], ["1" * 64, "2" * 64, "3" * 64, "4" * 64])
        self.assertEqual(ids["frontier_ledger_envelope_id"], "4" * 64)

    def test_multiple_late_freezes_fail_closed(self) -> None:
        freeze = {"pr_number": 42, "head_sha": "f" * 40, "transaction": {}}

        def fake_json(url, token):
            if "/actions/runs?" in url:
                return {"workflow_runs": [{"id": 9002, "name": "OVC tiered test selection shadow", "conclusion": "success"}]}
            return {"jobs": [{"id": 8002, "name": "OVC merge readiness", "conclusion": "success"}]}

        log = (
            b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=one\n"
            b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=two\n"
        )
        with (
            patch.object(TOOL, "_json", side_effect=fake_json),
            patch.object(TOOL, "_request_job_log", return_value=log),
            patch.object(TOOL, "decode_freeze_marker", return_value=freeze),
        ):
            with self.assertRaisesRegex(TOOL.PostMergeCompletionError, "expected one"):
                TOOL._freeze_from_physical_lane_logs(
                    repository="o/r", head_sha="f" * 40, pr_number=42, token="token"
                )


if __name__ == "__main__":
    unittest.main()
