from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.v0_4 import RO4IndexError, build_g2_evidence, validate_g2_evidence
from ovc.research_operations.v0_4.index_common import canonical_bytes, logical_hash, sha256_file

AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")


def axis(value: str, *, status: str = "EVALUATED", reason: str = "TEST") -> dict:
    return {"status": status, "value": value, "reason_code": reason}


def axes(motion: str, quality: str = "COHERENT", *, conflict: bool = False) -> dict:
    return {
        "LOCATION": axis("INSIDE_CONTAINER"),
        "MOTION": axis(motion),
        "ORGANISATION": axis("ORDERED"),
        "INTERACTION": axis("NO_INTERACTION"),
        "QUALITY": axis(
            "CONFLICT" if conflict else quality,
            status="CONFLICT" if conflict else "EVALUATED",
            reason="AMBIGUOUS_BOUNDARY" if conflict else "TEST",
        ),
    }


def create_partition(path: Path, *, role: str, side: str, clock: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE states(
          state_record_id TEXT PRIMARY KEY, release_id TEXT, manifest_sha256 TEXT, role TEXT,
          instrument TEXT, clock TEXT, side TEXT, evaluation_scope_id TEXT, interval_open TEXT,
          interval_close TEXT, first_valid_time TEXT, axes_json TEXT, axis_values_json TEXT,
          parent_c1_record_id TEXT, parent_opt_a_bar_id TEXT, continuity TEXT,
          source_line INTEGER, source_record_sha256 TEXT
        );
        CREATE TABLE transitions(
          transition_id TEXT PRIMARY KEY, release_id TEXT, role TEXT, clock TEXT, side TEXT,
          evaluation_scope_id TEXT, source_state_id TEXT, target_state_id TEXT,
          changed_axes_json TEXT, first_valid_time TEXT, continuity_status TEXT,
          source_line INTEGER, source_record_sha256 TEXT
        );
        """
    )
    if clock == "15M":
        times = ["2024-01-02T00:15:00Z", "2024-01-02T00:30:00Z", "2024-01-02T00:45:00Z"]
        records = [axes("BALANCED"), axes("BALANCED", conflict=True), axes("UP_PROGRESS")]
        continuity = ["RESET", "CONTIGUOUS", "RESET"]
    else:
        times = ["2024-01-02T00:00:00Z", "2024-01-02T02:00:00Z"]
        records = [axes("BALANCED"), axes("UP_PROGRESS")]
        continuity = ["RESET", "CONTIGUOUS"]
    release_id = f"OPT-B.C2.GBPUSD.{role}.v2"
    scope = "GBPUSD-15M-LOCAL-v0.1" if clock == "15M" else "GBPUSD-2H-A-L-LOCAL-v0.1"
    state_ids = []
    for index, (timestamp, state_axes, state_continuity) in enumerate(zip(times, records, continuity), 1):
        state_id = "c2-state:" + hashlib.sha256(f"{role}:{side}:{clock}:{index}".encode()).hexdigest()
        state_ids.append(state_id)
        values = {name: state_axes[name]["value"] for name in AXES}
        con.execute(
            "INSERT INTO states VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                state_id, release_id, "a" * 64, role, "GBPUSD", clock, side, scope,
                timestamp, timestamp, timestamp,
                json.dumps(state_axes, sort_keys=True, separators=(",", ":")),
                json.dumps(values, sort_keys=True, separators=(",", ":")),
                f"c1:{index}", f"opt-a:{index}", state_continuity, index, "b" * 64,
            ),
        )
    for index in range(1, len(state_ids)):
        changed = ["QUALITY"] if index == 1 and clock == "15M" else ["MOTION"]
        if index == 2 and clock == "15M":
            changed = ["MOTION", "QUALITY"]
        transition_id = "c2-transition:" + hashlib.sha256(
            f"{role}:{side}:{clock}:transition:{index}".encode()
        ).hexdigest()
        con.execute(
            "INSERT INTO transitions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                transition_id, release_id, role, clock, side, scope, state_ids[index - 1],
                state_ids[index], json.dumps(changed), times[index], "CONTIGUOUS", index, "c" * 64,
            ),
        )
    metadata = {
        "schema": "ovc-ro4-state-transition-index/v1",
        "partition_id": f"{role}.{clock}.{side}.TEST",
        "role": role,
        "clock": clock,
        "side": side,
        "evaluation_scope_id": scope,
        "release_id": release_id,
        "manifest_sha256": "a" * 64,
        "state_count": len(state_ids),
        "transition_count": len(state_ids) - 1,
    }
    con.executemany(
        "INSERT INTO metadata VALUES (?,?)",
        [(key, json.dumps(value, sort_keys=True, separators=(",", ":"))) for key, value in metadata.items()],
    )
    con.commit()
    con.close()
    return {
        **metadata,
        "index_file": path.name,
        "index_file_sha256": sha256_file(path),
        "index_size_bytes": path.stat().st_size,
    }


def materialize_index(root: Path) -> str:
    partitions = []
    for role in ("DISCOVERY", "DEVELOPMENT"):
        for side in ("BID", "ASK"):
            for clock in ("15M", "2H_A_L"):
                path = root / f"{role}.{clock}.{side}.TEST.sqlite"
                partitions.append(create_partition(path, role=role, side=side, clock=clock))
    core = {
        "schema": "ovc-ro4-g1-index-manifest/v1",
        "source_inventory_sha256": "d" * 64,
        "source_inventory_logical_hash": "e" * 64,
        "operation": "FULL_INDEX",
        "selected_partition": None,
        "partitions": sorted(partitions, key=lambda item: item["partition_id"]),
        "state_record_count": sum(item["state_count"] for item in partitions),
        "transition_record_count": sum(item["transition_count"] for item in partitions),
        "validation_consumption": "LOCKED_UNCONSUMED",
        "sampling_mode": "FULL_CORPUS_NO_SAMPLING",
        "authority": "LOCAL_REPLACEABLE_DERIVED",
    }
    core["logical_hash"] = logical_hash(core)
    (root / "index-manifest.json").write_bytes(canonical_bytes(core))
    return core["logical_hash"]


class RO4G2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.index_dir = self.root / "index"
        self.index_dir.mkdir()
        self.g1_hash = materialize_index(self.index_dir)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self, name: str = "g2"):
        return build_g2_evidence(index_dir=self.index_dir, output_dir=self.root / name)

    def test_build_and_validate(self) -> None:
        result = self.build()
        self.assertEqual(result.manifest["counts"]["matrices"], 40)
        self.assertEqual(result.manifest["counts"]["conflict_runs"], 4)
        self.assertEqual(result.manifest["counts"]["cross_scale_projections"], 12)
        self.assertEqual(validate_g2_evidence(self.root / "g2", self.g1_hash)["status"], "PASS")

    def test_output_is_byte_deterministic(self) -> None:
        first = self.build("first.sqlite")
        second = self.build("second.sqlite")
        self.assertEqual(first.manifest["logical_hash"], second.manifest["logical_hash"])
        first_hashes = {item["artifact_type"]: item["sha256"] for item in first.manifest["artifacts"]}
        second_hashes = {item["artifact_type"]: item["sha256"] for item in second.manifest["artifacts"]}
        self.assertEqual(first_hashes, second_hashes)

    def test_matrix_count_conservation_and_count_only_display(self) -> None:
        self.build()
        wrapper = json.loads((self.root / "g2/transition-matrices.json").read_text())
        self.assertTrue(wrapper["records"])
        for record in wrapper["records"]:
            self.assertEqual(
                record["total_transition_count"],
                record["eligible_denominator"] + record.get("missing_count", 0) + record.get("excluded_count", 0),
            )
            for cell in record["cells"]:
                self.assertIn(" of ", cell["display_text"])
                self.assertNotIn("%", cell["display_text"])

    def test_gap_terminates_persistence(self) -> None:
        self.build()
        count = 0
        invalid = 0
        with gzip.open(self.root / "g2/persistence-runs.jsonl.gz", "rt") as handle:
            for line in handle:
                record = json.loads(line)
                count += record["termination_reason"] == "GAP"
                invalid += record["duration_records"] != len(record["member_state_ids"])
        self.assertGreater(count, 0)
        self.assertEqual(invalid, 0)

    def test_conflicts_have_real_exact_controls_and_no_composite(self) -> None:
        self.build()
        wrapper = json.loads((self.root / "g2/conflict-runs.json").read_text())
        self.assertTrue(wrapper["records"])
        for record in wrapper["records"]:
            self.assertFalse({"winner", "composite_score", "severity_rank"}.intersection(record))
            self.assertGreaterEqual(len(record["participating_axes"]), 2)
            self.assertEqual(len(record["matched_control_ids"]), 1)

    def test_missing_real_control_blocks_build(self) -> None:
        path = self.index_dir / "DISCOVERY.15M.BID.TEST.sqlite"
        con = sqlite3.connect(path)
        normal = con.execute(
            "SELECT state_record_id FROM states WHERE json_extract(axes_json,'$.QUALITY.status')='EVALUATED' ORDER BY first_valid_time LIMIT 1"
        ).fetchone()[0]
        con.execute("UPDATE states SET axes_json=json_set(axes_json,'$.MOTION.value','DIFFERENT') WHERE state_record_id=?", (normal,))
        con.commit(); con.close()
        manifest = json.loads((self.index_dir / "index-manifest.json").read_text())
        part = next(item for item in manifest["partitions"] if item["index_file"] == path.name)
        part["index_file_sha256"] = sha256_file(path)
        core = dict(manifest); core.pop("logical_hash")
        manifest["logical_hash"] = logical_hash(core)
        (self.index_dir / "index-manifest.json").write_bytes(canonical_bytes(manifest))
        with self.assertRaisesRegex(RO4IndexError, "MATCHED_REAL_CONTROL_REQUIRED"):
            self.build()

    def test_cross_scale_parent_changes_are_explicit_and_no_override(self) -> None:
        self.build()
        changed = 0
        rows = []
        with gzip.open(self.root / "g2/cross-scale-alignment.jsonl.gz", "rt") as handle:
            for line in handle:
                record = json.loads(line)
                changed += record["parent_changed"]
                rows.append(record["axis_relations"])
        self.assertGreater(changed, 0)
        self.assertTrue(all(set(item) == set(AXES) for item in rows))

    def test_validation_denial_is_inherited(self) -> None:
        manifest = json.loads((self.index_dir / "index-manifest.json").read_text())
        manifest["validation_consumption"] = "AVAILABLE"
        (self.index_dir / "index-manifest.json").write_bytes(canonical_bytes(manifest))
        with self.assertRaisesRegex(RO4IndexError, "VALIDATION_DENIAL_NOT_PRESERVED"):
            self.build()

    def test_source_index_hash_mismatch_blocks(self) -> None:
        path = self.index_dir / "DISCOVERY.15M.ASK.TEST.sqlite"
        with path.open("ab") as handle:
            handle.write(b"tamper")
        with self.assertRaisesRegex(RO4IndexError, "RO4_G1_INDEX_HASH_MISMATCH"):
            self.build()


if __name__ == "__main__":
    unittest.main()
