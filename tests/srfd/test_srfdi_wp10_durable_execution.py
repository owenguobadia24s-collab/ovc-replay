from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd.wp10_durable_execution import (
    DurableExecutionError,
    RunArtifactStore,
    execute_durable_resumable_units,
)
from ovc.opt_b.srfd.wp10_execution_resilience import (
    RunAuthorityStore,
    RunBinding,
    RunCheckpointStore,
)


def binding() -> RunBinding:
    return RunBinding(
        programme_id="OVC-SRFD-BENCHMARK-v0.1",
        packet_id="SRFDI-WP10-v0.7",
        population_id="SRFD.POP.TEST",
        eligible_ids_sha256="1" * 64,
        scientific_manifest_sha256="2" * 64,
        preregistration_sha256="3" * 64,
        representation_pack_sha256="4" * 64,
        segmentation_pack_sha256="5" * 64,
        stability_pack_sha256="6" * 64,
        source_binding_sha256="7" * 64,
        capacity_grid_sha256="8" * 64,
        implementation_commit="9" * 64,
    )


def token(token_id: str, run_binding_sha256: str) -> dict[str, object]:
    return {
        "token_id": token_id,
        "state": "AUTHORIZED_UNCONSUMED",
        "single_use": True,
        "run_binding_sha256": run_binding_sha256,
    }


class SRFDIWP10DurableExecutionTests(unittest.TestCase):
    def test_interrupted_resume_skips_committed_artifacts(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            authority = RunAuthorityStore(root)
            start = authority.consume(token("SRFD.JUNE.AUTH.DURABLE", b.logical_hash), b)
            checkpoints = RunCheckpointStore(root)
            artifacts = RunArtifactStore(root)
            calls: list[str] = []

            def worker(unit_id: str) -> dict[str, str]:
                calls.append(unit_id)
                return {"unit_id": unit_id, "value": "out:" + unit_id}

            first = execute_durable_resumable_units(
                start=start,
                binding=b,
                checkpoint_store=checkpoints,
                artifact_store=artifacts,
                unit_ids=["u1", "u2", "u3"],
                worker=worker,
                stop_after_new_units=2,
            )
            self.assertFalse(first["complete"])
            self.assertEqual(["u1", "u2"], calls)
            second = execute_durable_resumable_units(
                start=authority.load(start.token_id),
                binding=b,
                checkpoint_store=checkpoints,
                artifact_store=artifacts,
                unit_ids=["u1", "u2", "u3"],
                worker=worker,
            )
            self.assertTrue(second["complete"])
            self.assertEqual(["u1", "u2", "u3"], calls)
            self.assertTrue(all(second["unit_artifact_sha256"].values()))

    def test_artifact_commit_before_checkpoint_is_idempotent(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            start = RunAuthorityStore(root).consume(
                token("SRFD.JUNE.AUTH.ORPHAN", b.logical_hash), b
            )
            artifacts = RunArtifactStore(root)
            output = {"unit": "u1", "value": 7}
            orphan = artifacts.commit_output(start, b, "u1", output)
            self.assertIsNotNone(orphan.artifact_sha256)
            calls: list[str] = []
            result = execute_durable_resumable_units(
                start=start,
                binding=b,
                checkpoint_store=RunCheckpointStore(root),
                artifact_store=artifacts,
                unit_ids=["u1"],
                worker=lambda unit: calls.append(unit) or output,
            )
            self.assertTrue(result["complete"])
            self.assertEqual(["u1"], calls)
            self.assertEqual(orphan.artifact_sha256, result["unit_artifact_sha256"]["u1"])

    def test_corrupt_artifact_fails_closed_on_resume(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            authority = RunAuthorityStore(root)
            start = authority.consume(token("SRFD.JUNE.AUTH.CORRUPT.ART", b.logical_hash), b)
            checkpoints = RunCheckpointStore(root)
            artifacts = RunArtifactStore(root)
            execute_durable_resumable_units(
                start=start,
                binding=b,
                checkpoint_store=checkpoints,
                artifact_store=artifacts,
                unit_ids=["u1"],
                worker=lambda unit: {"unit": unit},
            )
            artifact_path = next((root / "runs" / start.run_id / "artifacts").glob("*.json"))
            payload = json.loads(artifact_path.read_text())
            payload["output"]["unit"] = "tampered"
            artifact_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(DurableExecutionError) as ctx:
                execute_durable_resumable_units(
                    start=authority.load(start.token_id),
                    binding=b,
                    checkpoint_store=checkpoints,
                    artifact_store=artifacts,
                    unit_ids=["u1"],
                    worker=lambda unit: {"unit": unit},
                )
            self.assertEqual("ARTIFACT_CORRUPT", ctx.exception.reason_code)

    def test_external_quota_fails_before_artifact_commit(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            start = RunAuthorityStore(root).consume(
                token("SRFD.JUNE.AUTH.QUOTA", b.logical_hash), b
            )
            artifacts = RunArtifactStore(root, max_external_bytes=1)
            with self.assertRaises(DurableExecutionError) as ctx:
                artifacts.commit_output(start, b, "u1", {"payload": "too large"})
            self.assertEqual("CAPACITY_EXTERNAL_BYTES_EXCEEDED", ctx.exception.reason_code)


if __name__ == "__main__":
    unittest.main()
