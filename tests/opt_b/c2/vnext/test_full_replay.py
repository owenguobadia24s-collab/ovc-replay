from __future__ import annotations

import copy
import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from ovc.opt_b.c2_vnext import full_replay

ROOT = Path(__file__).resolve().parents[4]


@dataclass
class FakeBar:
    start_utc: str
    end_utc: str
    clock: str
    side: str
    quality_state: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    parent_source_object_ids: list[str]


def binding() -> dict:
    value = {
        "schema": full_replay.BINDING_SCHEMA,
        "binding_id": "C2VNEXT.JUNE.DISCOVERY.INPUT.v1",
        "programme_id": full_replay.PROGRAMME_ID,
        "plan_id": full_replay.PLAN_ID,
        "plan_version": full_replay.PLAN_VERSION,
        "packet_id": full_replay.PACKET_ID,
        "gate_id": full_replay.GATE_ID,
        "role": "DISCOVERY",
        "instrument": "GBPUSD",
        "source": {
            "slice_id": full_replay.SOURCE_SLICE_ID,
            "manifest_sha256": full_replay.SOURCE_MANIFEST_SHA256,
            "external_root": "C:/external",
            "files": [{
                "object_id": "SOURCE.M1.BID",
                "clock": "M1",
                "side": "BID",
                "relative_path": "source.csv",
                "row_count": 1,
                "size_bytes": 1,
                "sha256": "a" * 64,
                "schema_fingerprint": "schema",
                "first_timestamp_utc": "2026-05-30T00:00:00Z",
                "last_timestamp_utc": "2026-07-02T23:59:00Z"
            }],
            "provider_execution": "NONE",
            "legacy_c2_payload_use": "PROHIBITED"
        },
        "interval": {
            "context_start_utc": full_replay.CONTEXT_START,
            "target_start_utc": full_replay.TARGET_START,
            "target_end_exclusive_utc": full_replay.TARGET_END,
            "context_end_exclusive_utc": full_replay.CONTEXT_END,
            "target_eligibility": "TARGET_JUNE_ONLY"
        },
        "scope": {
            "clocks": list(full_replay.CLOCKS),
            "sides": list(full_replay.SIDES),
            "frames": ["LOCAL"],
            "opportunity_types": ["REGISTERED_SEQUENCE_WINDOW"],
            "object_families": ["AXIS_BUNDLE"],
            "sequence_lengths": list(full_replay.SEQUENCE_LENGTHS),
            "population_scope": "COMPLETE_REGISTERED_LAWFUL_DISCOVERY_POPULATION"
        },
        "code": {
            "expected_main_baseline": "1" * 40,
            "expected_code_commit": "2" * 40,
            "repository_files": [{"path": "x", "size_bytes": 1, "sha256": "b" * 64}],
            "repository_inventory_sha256": full_replay.sha_value([{"path": "x", "size_bytes": 1, "sha256": "b" * 64}])
        },
        "frozen_policy": {
            "integrated_freeze_id": full_replay.FREEZE_ID,
            "integrated_freeze_sha256": full_replay.FREEZE_SHA256,
            "method_registry_path": full_replay.METHOD_REGISTRY,
            "method_registry_sha256": "d" * 64,
            "method_pack_id": "C2.BOTTOM_UP.FUNCTIONAL.DISCOVERY.METHOD.v1",
            "discovery_view_id": "C2.DISCOVERY.VIEW.GBPUSD.SHADOW_FROZEN.v1",
            "maturity": "SHADOW_FROZEN"
        },
        "execution": {
            "max_runtime_seconds": 14400,
            "max_output_bytes": 10737418240,
            "clean_run_count": 2,
            "workspace_policy": "FRESH_PER_RUN",
            "checkpoint_policy": "SCOPE_ATOMIC",
            "resume_enabled": True,
            "exercise_restart": True
        },
        "requirements": {
            "readable_payloads": True,
            "complete_accounting": True,
            "first_valid_chronology": True,
            "identical_logical_hashes": True,
            "legacy_upstream_influence": False,
            "outcome_inputs": False,
            "validation_inputs": False
        },
        "authority": dict(full_replay.DENIED),
        "created_at_utc": "2026-08-05T10:00:00Z"
    }
    value["binding_sha256"] = full_replay.binding_hash(value)
    return value


class FullReplayTests(unittest.TestCase):
    def test_binding_is_hash_and_authority_closed(self) -> None:
        value = binding()
        with patch.object(full_replay, "git_head", return_value="2" * 40):
            self.assertEqual(value, full_replay.validate_binding(value, ROOT))
        tampered = copy.deepcopy(value)
        tampered["authority"]["active_selector"] = "ALLOWED"
        with patch.object(full_replay, "git_head", return_value="2" * 40):
            with self.assertRaisesRegex(full_replay.FullReplayError, "SHA256_MISMATCH"):
                full_replay.validate_binding(tampered, ROOT)
        tampered["binding_sha256"] = full_replay.binding_hash(tampered)
        with patch.object(full_replay, "git_head", return_value="2" * 40):
            with self.assertRaisesRegex(full_replay.FullReplayError, "AUTHORITY_MUST_REMAIN_DENIED"):
                full_replay.validate_binding(tampered, ROOT)

    def test_requests_preserve_warmup_complete_and_censored_units(self) -> None:
        bars = [
            FakeBar("2026-06-01T00:00:00Z", "2026-06-01T00:15:00Z", "15M", "BID", "COMPLETE", 1.0, 1.2, 0.9, 1.1, ["M1.1"]),
            FakeBar("2026-06-01T00:15:00Z", "2026-06-01T00:30:00Z", "15M", "BID", "COMPLETE", 1.1, 1.3, 1.0, 1.2, ["M1.2"]),
            FakeBar("2026-06-01T00:30:00Z", "2026-06-01T00:45:00Z", "15M", "BID", "QUARANTINED_INCOMPLETE_PARENT_SET", None, None, None, None, ["M1.3"])
        ]
        c1 = [
            {"c1_record_id": "C1.1", "first_valid_time": "2026-06-01T00:15:00Z"},
            {"c1_record_id": "C1.2", "first_valid_time": "2026-06-01T00:30:00Z"}
        ]
        requests = full_replay.build_scope_requests(
            bars, c1, clock="15M", side="BID",
            target_start="2026-06-01T00:00:00Z",
            target_end="2026-07-01T00:00:00Z",
            lengths=[2, 3], binding_sha256="a" * 64
        )
        self.assertEqual(6, len(requests))
        self.assertEqual(
            ["NOT_COMPUTABLE", "NOT_COMPUTABLE", "COMPUTABLE", "NOT_COMPUTABLE", "CENSORED", "CENSORED"],
            [item["computability_status"] for item in requests]
        )
        self.assertEqual([2, 3, 2, 3, 2, 3], [len(item["ordered_development"]) for item in requests])
        self.assertTrue(all(item["assurance"]["legacy_seed_count"] == 0 for item in requests))
        self.assertTrue(all(item["assurance"]["outcome_dependency_count"] == 0 for item in requests))
        self.assertTrue(all(item["assurance"]["validation_dependency_count"] == 0 for item in requests))

    def test_determinism_requires_clean_and_restart_equality(self) -> None:
        base = {
            "logical_population_sha256": "a" * 64,
            "artifact_inventory_sha256": "b" * 64,
            "manifest": {"counts": {"records": 10}}
        }
        passed = full_replay.compare_runs(base, copy.deepcopy(base), copy.deepcopy(base))
        self.assertEqual("PASS", passed["result"])
        changed = copy.deepcopy(base)
        changed["logical_population_sha256"] = "c" * 64
        failed = full_replay.compare_runs(base, changed, copy.deepcopy(base))
        self.assertEqual("FAIL", failed["result"])
        self.assertIn("LOGICAL_HASH", failed["discrepancies"])

    def test_repository_schema_and_operator_entrypoint(self) -> None:
        schema = json.loads((ROOT / "schemas/opt_b/c2/vnext/C2_VNEXT_FULL_REPLAY_INPUT_BINDING_v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(full_replay.BINDING_SCHEMA, schema["properties"]["schema"]["const"])
        self.assertEqual("DENIED", schema["properties"]["authority"]["properties"]["active_selector"]["const"])
        script = (ROOT / "scripts/c2ar/run_vnext_full_replay.ps1").read_text(encoding="utf-8")
        for command in ("build-binding", "preflight", "execute"):
            self.assertIn(command, script)
        self.assertIn("The repository worktree is not clean", script)
        self.assertIn("deny-legacy-upstream-influence", script)

    def test_cli_surface(self) -> None:
        parsed = full_replay.parser().parse_args([
            "build-binding", "--repository-root", str(ROOT),
            "--external-root", "C:/external", "--output", "C:/external/binding.json",
            "--expected-main-baseline", "1" * 40
        ])
        self.assertEqual("build-binding", parsed.command)


if __name__ == "__main__":
    unittest.main()
