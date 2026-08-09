from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd.wp10_execution_resilience import (
    ExecutionResilienceError,
    RunAuthorityStore,
    RunBinding,
    RunCheckpointStore,
    execute_resumable_units,
)


def binding(*, suffix: str = "a") -> RunBinding:
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
        implementation_commit=suffix * 64,
    )


def token(token_id: str, run_binding_sha256: str) -> dict[str, object]:
    return {
        "token_id": token_id,
        "state": "AUTHORIZED_UNCONSUMED",
        "single_use": True,
        "run_binding_sha256": run_binding_sha256,
    }


class SRFDIWP10ExecutionResilienceTests(unittest.TestCase):
    def test_single_use_token_starts_one_run_only(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            t = token("SRFD.JUNE.AUTH.TEST.ONE", b.logical_hash)
            store = RunAuthorityStore(root)
            start = store.consume(t, b)
            self.assertEqual("CONSUMED_FOR_RUN", start.state)
            self.assertEqual(start, store.load(str(t["token_id"])))
            with self.assertRaises(ExecutionResilienceError) as ctx:
                store.consume(t, b)
            self.assertEqual("TOKEN_ALREADY_CONSUMED", ctx.exception.reason_code)

    def test_resume_is_same_run_not_token_reuse_and_skips_committed_units(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            t = token("SRFD.JUNE.AUTH.TEST.RESUME", b.logical_hash)
            authority = RunAuthorityStore(root)
            checkpoints = RunCheckpointStore(root)
            start = authority.consume(t, b)
            calls: list[str] = []

            def worker(unit_id: str) -> dict[str, str]:
                calls.append(unit_id)
                return {"unit_id": unit_id, "value": f"out:{unit_id}"}

            first = execute_resumable_units(
                start=start,
                binding=b,
                checkpoint_store=checkpoints,
                unit_ids=["D01/C01", "D01/C02", "D02/C01", "D02/C02"],
                worker=worker,
                stop_after_new_units=2,
            )
            self.assertFalse(first["complete"])
            self.assertEqual(["D01/C01", "D01/C02"], calls)
            start_reloaded = authority.load(str(t["token_id"]))
            self.assertEqual(start.run_id, start_reloaded.run_id)
            second = execute_resumable_units(
                start=start_reloaded,
                binding=b,
                checkpoint_store=checkpoints,
                unit_ids=["D01/C01", "D01/C02", "D02/C01", "D02/C02"],
                worker=worker,
            )
            self.assertTrue(second["complete"])
            self.assertEqual(["D01/C01", "D01/C02", "D02/C01", "D02/C02"], calls)
            self.assertEqual(start.run_id, second["run_id"])
            self.assertEqual(4, second["completed_unit_count"])

    def test_interrupted_resume_matches_uninterrupted_scientific_unit_hashes(self) -> None:
        units = [f"D{d:02d}/C{c:02d}" for d in range(1, 4) for c in range(1, 4)]

        def worker(unit_id: str) -> dict[str, object]:
            return {"unit_id": unit_id, "score": sum(ord(ch) for ch in unit_id)}

        with TemporaryDirectory() as td1, TemporaryDirectory() as td2:
            b = binding()
            root1, root2 = Path(td1), Path(td2)
            a1, c1 = RunAuthorityStore(root1), RunCheckpointStore(root1)
            a2, c2 = RunAuthorityStore(root2), RunCheckpointStore(root2)
            s1 = a1.consume(token("SRFD.JUNE.AUTH.TEST.INTERRUPTED", b.logical_hash), b)
            s2 = a2.consume(token("SRFD.JUNE.AUTH.TEST.UNINTERRUPTED", b.logical_hash), b)
            execute_resumable_units(start=s1, binding=b, checkpoint_store=c1, unit_ids=units, worker=worker, stop_after_new_units=4)
            resumed = execute_resumable_units(start=a1.load("SRFD.JUNE.AUTH.TEST.INTERRUPTED"), binding=b, checkpoint_store=c1, unit_ids=units, worker=worker)
            uninterrupted = execute_resumable_units(start=s2, binding=b, checkpoint_store=c2, unit_ids=units, worker=worker)
            self.assertEqual(resumed["completed_units"], uninterrupted["completed_units"])
            self.assertEqual(resumed["unit_output_hashes"], uninterrupted["unit_output_hashes"])

    def test_resume_fails_closed_on_binding_drift(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            authority = RunAuthorityStore(root)
            checkpoints = RunCheckpointStore(root)
            start = authority.consume(token("SRFD.JUNE.AUTH.TEST.DRIFT", b.logical_hash), b)
            execute_resumable_units(start=start, binding=b, checkpoint_store=checkpoints, unit_ids=["u1"], worker=lambda u: {"u": u})
            changed = binding(suffix="b")
            with self.assertRaises(ExecutionResilienceError) as ctx:
                checkpoints.latest(start, changed)
            self.assertEqual("RESUME_BINDING_MISMATCH", ctx.exception.reason_code)

    def test_corrupt_checkpoint_fails_closed_and_uncommitted_temp_is_ignored(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            b = binding()
            authority = RunAuthorityStore(root)
            checkpoints = RunCheckpointStore(root)
            start = authority.consume(token("SRFD.JUNE.AUTH.TEST.CORRUPT", b.logical_hash), b)
            execute_resumable_units(start=start, binding=b, checkpoint_store=checkpoints, unit_ids=["u1"], worker=lambda u: {"u": u})
            run_dir = root / "runs" / start.run_id / "checkpoints"
            (run_dir / "00000002.json.tmp").write_text("partial")
            self.assertEqual(1, checkpoints.latest(start, b).sequence)
            path = run_dir / "00000001.json"
            payload = json.loads(path.read_text())
            payload["completed_units"] = ["tampered"]
            path.write_text(json.dumps(payload))
            with self.assertRaises(ExecutionResilienceError) as ctx:
                checkpoints.latest(start, b)
            self.assertEqual("CHECKPOINT_CORRUPT", ctx.exception.reason_code)

    def test_wrong_token_binding_never_starts(self) -> None:
        with TemporaryDirectory() as td:
            b = binding()
            wrong = token("SRFD.JUNE.AUTH.TEST.WRONG", "f" * 64)
            with self.assertRaises(ExecutionResilienceError) as ctx:
                RunAuthorityStore(Path(td)).consume(wrong, b)
            self.assertEqual("TOKEN_BINDING_MISMATCH", ctx.exception.reason_code)


if __name__ == "__main__":
    unittest.main()
