from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from ovc.opt_b.c2.replay import (
    DISCOVERY_MANIFEST,
    DISCOVERY_RELEASE,
    ReleaseBinding,
    ReplayError,
    run_role_replay,
    run_verified_role_replay,
    verify_canonical_release,
)


def fixture(record_id: str, close: str, open_: str, *, clock: str = "15M", side: str = "BID", minute: int = 15) -> dict:
    measurements = {
        "open": open_,
        "high": "1.2510",
        "low": "1.2480",
        "close": close,
        "range_low": "1.2400",
        "range_high": "1.2600",
        "swing_low": "1.2300",
        "swing_high": "1.2700",
        "prior_range": "0.0020",
    }
    for index in range(9, 18):
        measurements[f"m{index}"] = str(index)
    return {
        "c1_record_id": record_id,
        "c1_release_id": DISCOVERY_RELEASE,
        "c1_manifest_id": DISCOVERY_MANIFEST,
        "opt_a_release_id": "OPT-A.TEST",
        "opt_a_manifest_id": "MANIFEST.A.TEST",
        "role": "DISCOVERY",
        "authority_state": "ACTIVE_DISCOVERY",
        "instrument": "GBPUSD",
        "clock": clock,
        "side": side,
        "close_time": f"2026-01-01T00:{minute:02d}:00Z",
        "first_valid_time": f"2026-01-01T00:{minute:02d}:00Z",
        "measurements": measurements,
        "quality_state": "VALID",
    }


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_root(root: Path, records_by_path: dict[str, list[dict]]) -> tuple[Path, ReleaseBinding]:
    release = root / "discovery"
    files = release / "files"
    entries = []
    scopes: dict[tuple[str, str], int] = {}
    for relative, records in records_by_path.items():
        path = files / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
                for record in records:
                    handle.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode())
        entries.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": _hash(path)})
        parts = Path(relative).parts
        scopes[(parts[1], parts[2])] = scopes.get((parts[1], parts[2]), 0) + 1
    descriptor = files / "release-descriptor.json"
    descriptor.write_text(
        json.dumps(
            {
                "schema": "ovc-c1-release-descriptor/v1",
                "release_id": DISCOVERY_RELEASE,
                "role": "DISCOVERY",
                "formula_registry_id": "C1.FORMULAS.v0.1",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    entries.append({"path": "release-descriptor.json", "size_bytes": descriptor.stat().st_size, "sha256": _hash(descriptor)})
    manifest = release / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "ovc-c1-release-manifest/v1",
                "manifest_id": DISCOVERY_MANIFEST,
                "release_id": DISCOVERY_RELEASE,
                "files": entries,
                "file_count": len(entries),
                "payload_bytes": sum(item["size_bytes"] for item in entries),
                "record_file_count": len(records_by_path),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    binding = ReleaseBinding(
        "DISCOVERY",
        DISCOVERY_RELEASE,
        DISCOVERY_MANIFEST,
        _hash(manifest),
        len(records_by_path),
        len(entries),
        tuple((clock, side, count) for (clock, side), count in sorted(scopes.items())),
    )
    return release, binding


class WP5ReplayTests(unittest.TestCase):
    def test_plain_export_replay_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.jsonl"
            source.write_text(
                "\n".join(json.dumps(x) for x in [fixture("C1.1", "1.2500", "1.2490"), fixture("C1.2", "1.2485", "1.2495", minute=30)]) + "\n",
                encoding="utf-8",
            )
            first = run_role_replay(role="DISCOVERY", release_id=DISCOVERY_RELEASE, input_path=source, output_dir=root / "a")
            second = run_role_replay(role="DISCOVERY", release_id=DISCOVERY_RELEASE, input_path=source, output_dir=root / "b")
            self.assertEqual(first, second)
            self.assertEqual((root / "a" / "discovery_states.jsonl").read_bytes(), (root / "b" / "discovery_states.jsonl").read_bytes())
            self.assertEqual(first.state_records, 2)
            self.assertEqual(first.transition_records, 1)

    def test_manifest_bound_gzip_shards_are_fully_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release, binding = canonical_root(
                Path(tmp),
                {
                    "records/15M/BID/a.c1.jsonl.gz": [fixture("C1.1", "1.2500", "1.2490")],
                    "records/2H_A_L/ASK/b.c1.jsonl.gz": [fixture("C1.2", "1.2485", "1.2495", clock="2H_A_L", side="ASK")],
                },
            )
            verified = verify_canonical_release(release, binding)
            self.assertEqual(len(verified.record_paths), 2)
            self.assertEqual(verified.payload_object_count, 3)
            self.assertEqual(verified.canonical_object_count, 4)

    def test_changed_shard_is_rejected_before_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release, binding = canonical_root(
                Path(tmp), {"records/15M/BID/a.c1.jsonl.gz": [fixture("C1.1", "1.2500", "1.2490")]}
            )
            shard = release / "files" / "records" / "15M" / "BID" / "a.c1.jsonl.gz"
            shard.write_bytes(shard.read_bytes() + b"x")
            with self.assertRaisesRegex(ReplayError, "PAYLOAD_SIZE_MISMATCH"):
                verify_canonical_release(release, binding)

    def test_persistence_and_transitions_never_cross_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release, binding = canonical_root(
                Path(tmp),
                {
                    "records/15M/BID/a.c1.jsonl.gz": [
                        fixture("C1.1", "1.2500", "1.2490"),
                        fixture("C1.2", "1.2485", "1.2495", minute=30),
                    ],
                    "records/2H_A_L/ASK/b.c1.jsonl.gz": [
                        fixture("C1.3", "1.2500", "1.2490", clock="2H_A_L", side="ASK"),
                        fixture("C1.4", "1.2485", "1.2495", clock="2H_A_L", side="ASK", minute=30),
                    ],
                },
            )
            summary = run_verified_role_replay(verify_canonical_release(release, binding), Path(tmp) / "out")
            self.assertEqual(summary.scope_count, 2)
            self.assertEqual(summary.state_records, 4)
            self.assertEqual(summary.transition_records, 2)

    def test_published_c1_primitive_shape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            actual = {
                "schema": "ovc-c1-bar-primitives/v0.1",
                "record_id": "c1:" + "0" * 64,
                "role": "DISCOVERY",
                "parent_release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
                "parent_manifest_id": "MANIFEST.OPT-A.TEST",
                "instrument": "GBPUSD",
                "clock": "15M",
                "price_side": "BID",
                "timestamp_ms": 1609459200000,
                "measurements": {"range_abs": "0.001"},
            }
            release, binding = canonical_root(Path(tmp), {"records/15M/BID/a.c1.jsonl.gz": [actual]})
            verified = verify_canonical_release(release, binding)
            with self.assertRaisesRegex(ReplayError, "PUBLISHED_C1_RECORD_SHAPE_NOT_C2_HANDOFF_ENVELOPE"):
                run_verified_role_replay(verified, Path(tmp) / "out")

    def test_wrong_manifest_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release, binding = canonical_root(
                Path(tmp), {"records/15M/BID/a.c1.jsonl.gz": [fixture("C1.1", "1.2500", "1.2490")]}
            )
            wrong = replace(binding, manifest_id="MANIFEST.C1.WRONG")
            with self.assertRaisesRegex(ReplayError, "WRONG_MANIFEST_ID"):
                verify_canonical_release(release, wrong)


if __name__ == "__main__":
    unittest.main()
