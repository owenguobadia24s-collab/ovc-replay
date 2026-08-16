from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable

from .canonical import canonical_json_bytes
from .generation import FAMILY_ID_KEYS, PARTITIONS, GenerationBundle, verify_generation_bundle


class AtlasGraphStoreError(ValueError):
    """Raised when the disposable Atlas SQLite store fails integrity checks."""


class GraphStore:
    """Disposable SQLite index over one immutable Atlas generation bundle."""

    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def rebuild(self, bundle: GenerationBundle) -> dict[str, Any]:
        verify_generation_bundle(bundle)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                DROP TABLE IF EXISTS atlas_object;
                DROP TABLE IF EXISTS atlas_edge;
                DROP TABLE IF EXISTS atlas_metadata;
                CREATE TABLE atlas_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE atlas_object (
                    family TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    partition_name TEXT NOT NULL,
                    canonical_json BLOB NOT NULL,
                    PRIMARY KEY (family, object_id)
                );
                CREATE TABLE atlas_edge (
                    relationship_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    partition_name TEXT NOT NULL
                );
                CREATE INDEX atlas_object_partition ON atlas_object(partition_name, family);
                CREATE INDEX atlas_edge_subject ON atlas_edge(subject_id, predicate);
                CREATE INDEX atlas_edge_object ON atlas_edge(object_id, predicate);
                    """
                )
                connection.execute("INSERT INTO atlas_metadata VALUES (?, ?)", ("root_hash", bundle.root_hash))
                connection.execute("INSERT INTO atlas_metadata VALUES (?, ?)", ("graph_logical_hash", bundle.root_manifest["graph_logical_hash"]))
                for partition in PARTITIONS:
                    for family, identity_key in FAMILY_ID_KEYS.items():
                        raw = bundle.files[f"partitions/{partition}/{family}.jsonl"]
                        for line in raw.splitlines():
                            row = json.loads(line)
                            object_id = row[identity_key]
                            connection.execute(
                                "INSERT INTO atlas_object VALUES (?, ?, ?, ?)",
                                (family, object_id, partition, canonical_json_bytes(row)),
                            )
                            if family == "relationships":
                                connection.execute(
                                    "INSERT INTO atlas_edge VALUES (?, ?, ?, ?, ?)",
                                    (object_id, row["subject_id"], row["object_id"], row["predicate"], partition),
                                )
        return {"status": "PASS", "root_hash": bundle.root_hash, "counts": self.counts(), "authority_effect": "NONE_DISPOSABLE_INDEX"}

    def root_hash(self) -> str | None:
        with closing(self._connect()) as connection:
            try:
                row = connection.execute("SELECT value FROM atlas_metadata WHERE key='root_hash'").fetchone()
            except sqlite3.OperationalError:
                return None
        return None if row is None else str(row[0])

    def counts(self) -> dict[str, int]:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT family, COUNT(*) AS count FROM atlas_object GROUP BY family").fetchall()
        return {str(row["family"]): int(row["count"]) for row in rows}

    def object_by_id(self, family: str, object_id: str, *, allowed_partitions: Iterable[str]) -> dict[str, Any] | None:
        allowed = tuple(sorted(set(allowed_partitions)))
        if not allowed:
            return None
        placeholders = ",".join("?" for _ in allowed)
        with closing(self._connect()) as connection:
            row = connection.execute(
                f"SELECT canonical_json FROM atlas_object WHERE family=? AND object_id=? AND partition_name IN ({placeholders})",
                (family, object_id, *allowed),
            ).fetchone()
        return None if row is None else json.loads(bytes(row[0]))

    def adjacent(self, entity_id: str, *, allowed_partitions: Iterable[str]) -> list[dict[str, Any]]:
        allowed = tuple(sorted(set(allowed_partitions)))
        if not allowed:
            return []
        placeholders = ",".join("?" for _ in allowed)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"SELECT relationship_id, subject_id, object_id, predicate, partition_name FROM atlas_edge WHERE (subject_id=? OR object_id=?) AND partition_name IN ({placeholders}) ORDER BY relationship_id",
                (entity_id, entity_id, *allowed),
            ).fetchall()
        return [dict(row) for row in rows]
