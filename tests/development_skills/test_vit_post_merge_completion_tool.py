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
                "https://api.github.com/repos/o/r/actions/jobs/123/logs",
                "token",
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
                "User-Agent": "ovc-vit-local-post-merge-completion/v1",
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
        self.assertEqual(
            redirected.full_url,
            "https://signed-log-storage.example/job-log",
        )

    def test_non_log_request_remains_fail_closed_on_401(self) -> None:
        calls = []

        def fake_urlopen(request, timeout=30):
            calls.append(request)
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

        with patch.object(TOOL, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(TOOL.PostMergeCompletionError):
                TOOL._request("https://api.github.com/repos/o/r", "token")

        self.assertEqual(len(calls), 1)

    def test_freeze_lookup_scopes_redirect_aware_download_to_job_log(self) -> None:
        freeze = {
            "pr_number": 42,
            "head_sha": "f" * 40,
            "transaction": {},
        }
        calls = []

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

        def fake_job_log(url, token):
            calls.append(url)
            return b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=payload"

        with (
            patch.object(TOOL, "_json", side_effect=fake_json),
            patch.object(TOOL, "_request_job_log", side_effect=fake_job_log),
            patch.object(TOOL, "decode_freeze_marker", return_value=freeze),
        ):
            observed = TOOL._freeze_from_prewrite_logs(
                repository="o/r",
                head_sha="f" * 40,
                pr_number=42,
                token="token",
            )

        self.assertEqual(observed, freeze)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].endswith("/actions/jobs/8001/logs"))


if __name__ == "__main__":
    unittest.main()
