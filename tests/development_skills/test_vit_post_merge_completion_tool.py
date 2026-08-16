from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


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


class VitPostMergeCompletionToolTests(unittest.TestCase):
    def test_request_uses_supported_github_media_type_for_job_logs(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["accept"] = request.get_header("Accept")
            captured["url"] = request.full_url
            return _Response(b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=abc")

        with patch.object(TOOL, "urlopen", side_effect=fake_urlopen):
            body = TOOL._request(
                "https://api.github.com/repos/o/r/actions/jobs/123/logs",
                "token",
            )

        self.assertEqual(captured["accept"], "application/vnd.github+json")
        self.assertTrue(str(captured["url"]).endswith("/actions/jobs/123/logs"))
        self.assertIn(b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64", body)

    def test_job_log_request_retries_401_without_authorization_when_explicitly_allowed(self) -> None:
        requests = []

        def fake_urlopen(request, timeout=30):
            requests.append(request)
            if len(requests) == 1:
                raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)
            return _Response(b"public-job-log")

        with patch.object(TOOL, "urlopen", side_effect=fake_urlopen):
            body = TOOL._request(
                "https://api.github.com/repos/o/r/actions/jobs/123/logs",
                "token",
                allow_public_unauthenticated_retry=True,
            )

        self.assertEqual(body, b"public-job-log")
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer token")
        self.assertIsNone(requests[1].get_header("Authorization"))
        self.assertEqual(requests[1].get_header("Accept"), "application/vnd.github+json")

    def test_non_log_request_does_not_retry_401_by_default(self) -> None:
        calls = []

        def fake_urlopen(request, timeout=30):
            calls.append(request)
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

        with patch.object(TOOL, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(TOOL.PostMergeCompletionError):
                TOOL._request("https://api.github.com/repos/o/r", "token")

        self.assertEqual(len(calls), 1)

    def test_freeze_lookup_scopes_public_retry_to_job_log_request(self) -> None:
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

        def fake_request(url, token, **kwargs):
            calls.append((url, kwargs))
            return b"OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=payload"

        with (
            patch.object(TOOL, "_json", side_effect=fake_json),
            patch.object(TOOL, "_request", side_effect=fake_request),
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
        self.assertEqual(calls[0][1], {"allow_public_unauthenticated_retry": True})


if __name__ == "__main__":
    unittest.main()
