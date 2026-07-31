from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from ovc.research_operations.v0_4 import (
    DeclaredSampleRequired,
    RO4IndexError,
    build_sequence_partition,
    declared_distance,
    diversity_audit,
    finalize_sequence_evidence,
    validate_sequence_evidence,
    workspace_inventory,
)
from ovc.research_operations.v0_4.index_common import AXES, canonical_bytes, logical_hash, sha256_file
from ovc.research_operations.v0_4.sequence_common import signature_core


def axis(value: str, *, status: str = "EVALUATED", reason: str = "SYNTHETIC") -> dict:
    return {"status": status, "value": value, "reason_code": reason}


def axes(index: int, unique: bool = False) -> dict:
    suffix = f"U{index}" if unique else str(index % 4)
    return {
        "LOCATION": axis("L" + suffix),
        "MOTION": axis("M" + str(index % 3)),
        "ORGANISATION": axis("O" + str(index % 2)),
        "INTERACTION": axis("I" + str(index % 5)),
        "QUALITY": axis("COHERENT"),
    }


def create_partition(path: Path, *, partition_id: str, role: str, side: str, count: int = 96) -> dict:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE states(
          state_record_id TEXT PRIMARY KEY,release_id TEXT,manifest_sha256 TEXT,role TEXT,instrument TEXT,
          clock TEXT,side TEXT,evaluation_scope_id TEXT,interval_open TEXT,interval_close TEXT,
          first_valid_time TEXT,axes_json TEXT,axis_values_json TEXT,parent_c1_record_id TEXT,
          parent_opt_a_bar_id TEXT,continuity TEXT,source_line INTEGER,source_record_sha256 TEXT
        );
        CREATE TABLE transitions(
          transition_id TEXT PRIMARY KEY,release_id TEXT,role TEXT,clock TEXT,side TEXT,evaluation_scope_id TEXT,
          source_state_id TEXT,target_state_id TEXT,changed_axes_json TEXT,first_valid_time TEXT,
          continuity_status TEXT,source_line INTEGER,source_record_sha256 TEXT
        );
        """
    )
    release_id = f"OPT-B.C2.GBPUSD.{role}.SYNTHETIC.v2"
    scope = "GBPUSD-15M-LOCAL-v0.1"
    start = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
    state_ids = []
    axis_rows = []
    for index in range(count):
        first_valid = start + timedelta(minutes=15 * (index + 1))
        state_id = "c2-state:" + hashlib.sha256(f"{partition_id}:{index}".encode()).hexdigest()
        state_axes = axes(index, unique=(index % 29 == 0 and index > 0))
        values = {name: state_axes[name]["value"] for name in AXES}
        continuity = "RESET" if index in {0, 48} else "CONTIGUOUS"
        con.execute(
            "INSERT INTO states VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                state_id, release_id, "a" * 64, role, "GBPUSD", "15M", side, scope,
                first_valid.isoformat().replace("+00:00", "Z"), first_valid.isoformat().replace("+00:00", "Z"),
                first_valid.isoformat().replace("+00:00", "Z"),
                json.dumps(state_axes, sort_keys=True, separators=(",", ":")),
                json.dumps(values, sort_keys=True, separators=(",", ":")),
                f"c1:{index}", f"opt-a:{index}", continuity, index + 1, "b" * 64,
            ),
        )
        state_ids.append(state_id); axis_rows.append(state_axes)
    transition_count = 0
    for index in range(1, count):
        if index == 48:
            continue
        changed = [name for name in AXES if axis_rows[index - 1][name] != axis_rows[index][name]]
        transition_id = "c2-transition:" + hashlib.sha256(f"{partition_id}:t:{index}".encode()).hexdigest()
        first_valid = start + timedelta(minutes=15 * (index + 1))
        con.execute(
            "INSERT INTO transitions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                transition_id, release_id, role, "15M", side, scope, state_ids[index - 1], state_ids[index],
                json.dumps(changed, separators=(",", ":")), first_valid.isoformat().replace("+00:00", "Z"),
                "CONTIGUOUS", index, "c" * 64,
            ),
        )
        transition_count += 1
    metadata = {
        "schema": "ovc-ro4-state-transition-index/v1", "partition_id": partition_id,
        "role": role, "clock": "15M", "side": side, "evaluation_scope_id": scope,
        "release_id": release_id, "manifest_sha256": "a" * 64, "state_count": count,
        "transition_count": transition_count, "first_valid_time": "2024-01-02T00:15:00Z",
        "last_valid_time": (start + timedelta(minutes=15 * count)).isoformat().replace("+00:00", "Z"),
        "partition_logical_hash": "d" * 64, "state_logical_hash": "e" * 64,
        "transition_logical_hash": "f" * 64,
    }
    con.executemany(
        "INSERT INTO metadata VALUES (?,?)",
        [(key, json.dumps(value, sort_keys=True, separators=(",", ":"))) for key, value in metadata.items()],
    )
    con.commit(); con.close()
    return {
        "partition_id": partition_id, "role": role, "clock": "15M", "side": side,
        "evaluation_scope_id": scope, "index_file": path.name,
        "index_file_sha256": sha256_file(path), "index_size_bytes": path.stat().st_size,
        "state_count": count, "transition_count": transition_count,
    }


def materialize_index(root: Path) -> str:
    parts = []
    for role in ("DISCOVERY", "DEVELOPMENT"):
        for side in ("BID", "ASK"):
            partition_id = f"{role}.15M.{side}.SYNTHETIC"
            parts.append(create_partition(root / f"{partition_id}.sqlite", partition_id=partition_id, role=role, side=side))
    core = {
        "schema": "ovc-ro4-g1-index-manifest/v1", "source_inventory_sha256": "1" * 64,
        "source_inventory_logical_hash": "2" * 64, "operation": "FULL_INDEX",
        "selected_partition": None, "partitions": sorted(parts, key=lambda item: item["partition_id"]),
        "state_record_count": sum(item["state_count"] for item in parts),
        "transition_record_count": sum(item["transition_count"] for item in parts),
        "validation_consumption": "LOCKED_UNCONSUMED", "sampling_mode": "FULL_CORPUS_NO_SAMPLING",
        "authority": "LOCAL_REPLACEABLE_DERIVED",
    }
    core["logical_hash"] = logical_hash(core)
    (root / "index-manifest.json").write_bytes(canonical_bytes(core))
    return core["logical_hash"]


class RO4G3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.index_dir = self.root / "index"; self.index_dir.mkdir()
        self.g1_hash = materialize_index(self.index_dir)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self, name: str = "g3"):
        output = self.root / name; output.mkdir()
        workspace = output / "sequence-population.sqlite"
        manifest = json.loads((self.index_dir / "index-manifest.json").read_text())
        for part in manifest["partitions"]:
            build_sequence_partition(index_dir=self.index_dir, workspace_path=workspace, partition_id=part["partition_id"])
        result = finalize_sequence_evidence(index_dir=self.index_dir, workspace_path=workspace, output_dir=output)
        return output, result

    def test_full_build_and_validate(self) -> None:
        output, result = self.build()
        self.assertGreater(result.manifest["window_count"], 1000)
        self.assertGreaterEqual(result.manifest["recurrence_candidate_count"], 10)
        checked = validate_sequence_evidence(output, self.g1_hash)
        self.assertEqual(checked["status"], "PASS")

    def test_byte_deterministic_rerun(self) -> None:
        first, r1 = self.build("first")
        second, r2 = self.build("second")
        self.assertEqual(r1.manifest["logical_hash"], r2.manifest["logical_hash"])
        for name in (
            "neutral-recurrence-candidates.jsonl.gz", "real-control-ledger.jsonl.gz",
            "blinded-review-batch.json", "sealed-answer-key.json", "signature-diversity-audit.json",
        ):
            self.assertEqual(sha256_file(first / name), sha256_file(second / name))

    def test_gap_breaks_windows(self) -> None:
        output, _ = self.build()
        inventory = json.loads((output / "sequence-population-inventory.json").read_text())
        self.assertTrue(all(item["window_count"] > 0 for item in inventory["partitions"]))
        workspace = sqlite3.connect(output / "sequence-population.sqlite")
        try:
            crossing = workspace.execute(
                "SELECT COUNT(*) FROM windows WHERE start_index < 48 AND end_index >= 48"
            ).fetchone()[0]
            self.assertEqual(crossing, 0)
        finally:
            workspace.close()

    def test_window_cap_requires_declared_sample(self) -> None:
        import ovc.research_operations.v0_4.sequence_workspace as module
        workspace = self.root / "cap.sqlite"
        part = json.loads((self.index_dir / "index-manifest.json").read_text())["partitions"][0]
        with mock.patch.object(module, "WINDOW_CAP", 10):
            with self.assertRaises(DeclaredSampleRequired):
                build_sequence_partition(index_dir=self.index_dir, workspace_path=workspace, partition_id=part["partition_id"])

    def test_declared_distance_is_component_visible_and_deterministic(self) -> None:
        left = signature_core(
            role="DISCOVERY", clock="15M", side="BID", evaluation_scope_id="GBPUSD-15M-LOCAL-v0.1",
            state_axes=[axes(1), axes(2)], changed_axes=[["MOTION"]],
        )
        right = json.loads(json.dumps(left)); right["ordered_axis_vectors"][0]["MOTION"]["value"] = "MUTATED"
        first = declared_distance(left, right); second = declared_distance(left, right)
        self.assertEqual(first, second)
        self.assertGreater(first["components"]["axis_mismatch"]["raw"], 0)
        self.assertEqual(first["learned_weights"], "PROHIBITED")

    def test_diversity_thresholds(self) -> None:
        self.assertEqual(diversity_audit("balanced", [1] * 100)["status"], "PASS")
        self.assertEqual(diversity_audit("small", [1] * 99)["status"], "INSUFFICIENT_SAMPLE_FOR_DIVERSITY_AUDIT")
        self.assertEqual(diversity_audit("concentrated", [90] + [1] * 20)["status"], "SIGNATURE_CONCENTRATION_WARNING")

    def test_blinding_pd_isolation_and_synthetic_exclusion(self) -> None:
        output, _ = self.build()
        batch = json.loads((output / "blinded-review-batch.json").read_text())
        self.assertTrue(batch["blinded"])
        self.assertEqual(batch["composition"]["synthetic_controls"], 0)
        self.assertTrue(all("true_class" not in card for card in batch["cards"]))
        pd = json.loads((output / "pd-isolation-assurance.json").read_text())
        self.assertEqual(pd["result"], "PASS")
        self.assertEqual(pd["population_merge"], "DENIED")

    def test_machine_ablation_is_not_operator_facing(self) -> None:
        output, _ = self.build()
        assurance = json.loads((output / "machine-only-ablation-assurance.json").read_text())
        self.assertEqual(assurance["result"], "PASS")
        self.assertEqual(assurance["operator_surface_state"], "DENIED")
        self.assertEqual(assurance["operator_facing_artifacts"], [])

    def test_source_hash_mismatch_blocks(self) -> None:
        part = json.loads((self.index_dir / "index-manifest.json").read_text())["partitions"][0]
        with (self.index_dir / part["index_file"]).open("ab") as handle:
            handle.write(b"tamper")
        with self.assertRaisesRegex(RO4IndexError, "RO4_G1_INDEX_HASH_MISMATCH"):
            build_sequence_partition(index_dir=self.index_dir, workspace_path=self.root / "bad.sqlite", partition_id=part["partition_id"])

    def test_incremental_partition_rebuild_preserves_unchanged_hashes(self) -> None:
        workspace = self.root / "incremental.sqlite"
        manifest = json.loads((self.index_dir / "index-manifest.json").read_text())
        for part in manifest["partitions"]:
            build_sequence_partition(index_dir=self.index_dir, workspace_path=workspace, partition_id=part["partition_id"])
        before = {item["partition_id"]: item["logical_hash"] for item in workspace_inventory(workspace)["partitions"]}
        selected = manifest["partitions"][0]["partition_id"]
        build_sequence_partition(index_dir=self.index_dir, workspace_path=workspace, partition_id=selected)
        after = {item["partition_id"]: item["logical_hash"] for item in workspace_inventory(workspace)["partitions"]}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
