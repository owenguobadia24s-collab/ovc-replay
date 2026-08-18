from __future__ import annotations

"""Deterministic C2P2 scientific-discrimination ledger tooling.

This module is synthetic/read-only until a separately approved C2P2-SD-GREAL
real-source authority exists. It never selects or activates an ObjectPack,
consumes Validation, or uses future outcomes. Hard breaks are accepted only as
candidate-independent confirmed evidence supplied by the caller.
"""

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping

PROGRAMME_ID = "OVC-C2P2-SCIENTIFIC-DISCRIMINATION-v0.1"
ALLOWED_DISPOSITIONS = frozenset({"SAME", "DIFFERENT", "AMBIGUOUS", "NO_CORRESPONDENCE"})
HARD_BREAK_IDS = frozenset({
    "EXPLICIT_UPSTREAM_INVALIDATION",
    "DECLARED_STRUCTURAL_ROLE_CHANGE",
    "DECLARED_GEOMETRY_KIND_CHANGE",
    "SPLIT_PARENT_DISPOSITION",
    "MERGE_PARENT_DISPOSITION",
    "REQUIRED_SOURCE_DISCONTINUITY",
})
CANDIDATE_IDS = (
    "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
    "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v3",
    "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v3",
)
FORBIDDEN_REVIEW_FIELDS = frozenset({
    "candidate_id", "semantic_candidate_id", "object_count", "compression_ratio",
    "runtime_seconds", "future_outcome", "future_price", "family", "C3_semantics",
    "selection_preference",
})


class ScientificDiscriminationError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def make_edge(
    *,
    prior_source_record_id: str,
    current_source_record_id: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    instrument: str,
    side: str,
    clock: str,
    structural_role_id: str,
    geometry_kind_id: str,
    candidate_dispositions: Mapping[str, str],
    confirmed_hard_breaks: Iterable[str] = (),
    owner_constitution_evidence: Mapping[str, Any] | None = None,
    review_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = {
        "schema": "ovc-c2p2-sd-edge-identity/v1",
        "prior_source_record_id": prior_source_record_id,
        "current_source_record_id": current_source_record_id,
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": evaluation_cutoff,
        "instrument": instrument,
        "side": side,
        "clock": clock,
        "structural_role_id": structural_role_id,
        "geometry_kind_id": geometry_kind_id,
    }
    return {
        **identity,
        "edge_id": _hash(identity),
        "candidate_dispositions": dict(candidate_dispositions),
        "independent_anchor_evidence": {
            "confirmed_hard_breaks": sorted(set(confirmed_hard_breaks)),
            "owner_constitution_evidence": dict(owner_constitution_evidence or {}),
        },
        "review_context": dict(review_context or {}),
    }


def _validate_edge(edge: Mapping[str, Any]) -> None:
    required = {
        "edge_id", "prior_source_record_id", "current_source_record_id", "first_valid_time",
        "evaluation_cutoff", "instrument", "side", "clock", "structural_role_id",
        "geometry_kind_id", "candidate_dispositions", "independent_anchor_evidence",
    }
    if not required.issubset(edge):
        raise ScientificDiscriminationError("SD_EDGE_INCOMPLETE")
    identity = {key: edge[key] for key in (
        "schema", "prior_source_record_id", "current_source_record_id", "first_valid_time",
        "evaluation_cutoff", "instrument", "side", "clock", "structural_role_id", "geometry_kind_id",
    )}
    if identity.get("schema") != "ovc-c2p2-sd-edge-identity/v1" or edge["edge_id"] != _hash(identity):
        raise ScientificDiscriminationError("SD_EDGE_IDENTITY_INVALID")
    dispositions = edge["candidate_dispositions"]
    if not isinstance(dispositions, Mapping) or set(dispositions) != set(CANDIDATE_IDS):
        raise ScientificDiscriminationError("SD_EDGE_CANDIDATE_SET_INVALID")
    if any(value not in ALLOWED_DISPOSITIONS for value in dispositions.values()):
        raise ScientificDiscriminationError("SD_EDGE_DISPOSITION_INVALID")
    anchor = edge["independent_anchor_evidence"]
    if not isinstance(anchor, Mapping):
        raise ScientificDiscriminationError("SD_EDGE_ANCHOR_INVALID")
    breaks = anchor.get("confirmed_hard_breaks", [])
    if not isinstance(breaks, list) or not set(breaks).issubset(HARD_BREAK_IDS):
        raise ScientificDiscriminationError("SD_EDGE_HARD_BREAK_INVALID")
    if edge["first_valid_time"] > edge["evaluation_cutoff"]:
        raise ScientificDiscriminationError("SD_EDGE_FUTURE_INFORMATION")


def analyze_edge(edge: Mapping[str, Any]) -> dict[str, Any]:
    _validate_edge(edge)
    dispositions = dict(edge["candidate_dispositions"])
    breaks = sorted(set(edge["independent_anchor_evidence"].get("confirmed_hard_breaks", [])))
    hard_falsifications = sorted(
        candidate_id for candidate_id, disposition in dispositions.items()
        if breaks and disposition == "SAME"
    )
    values = list(dispositions.values())
    candidate_disagreement = len(set(values)) > 1
    include = candidate_disagreement or bool(breaks)
    stratum = {
        "year": int(str(edge["first_valid_time"])[:4]),
        "side": edge["side"],
        "clock": edge["clock"],
        "structural_role_id": edge["structural_role_id"],
        "geometry_kind_id": edge["geometry_kind_id"],
    }
    signature_material = {
        "schema": "ovc-c2p2-sd-disagreement-signature/v1",
        "candidate_dispositions": dispositions,
        "confirmed_hard_breaks": breaks,
    }
    return {
        "schema": "ovc-c2p2-scientific-discrimination-ledger-row/v1",
        "edge_id": edge["edge_id"],
        "prior_source_record_id": edge["prior_source_record_id"],
        "current_source_record_id": edge["current_source_record_id"],
        "first_valid_time": edge["first_valid_time"],
        "evaluation_cutoff": edge["evaluation_cutoff"],
        "stratum": stratum,
        "candidate_dispositions": dispositions,
        "confirmed_hard_breaks": breaks,
        "hard_falsification_candidate_ids": hard_falsifications,
        "candidate_disagreement": candidate_disagreement,
        "include_in_disagreement_ledger": include,
        "disagreement_signature": _hash(signature_material),
        "owner_constitution_evidence": dict(edge["independent_anchor_evidence"].get("owner_constitution_evidence", {})),
        "review_context": dict(edge.get("review_context", {})),
        "automatic_scientific_label": "DIFFERENT" if breaks else None,
    }


def _blind_mapping(edge_id: str, blinding_key: str) -> dict[str, str]:
    ordered = sorted(CANDIDATE_IDS, key=lambda candidate_id: sha256(f"{blinding_key}|{edge_id}|{candidate_id}".encode()).hexdigest())
    return {slot: candidate_id for slot, candidate_id in zip(("X", "Y", "Z"), ordered, strict=True)}


def build_blind_review_card(record: Mapping[str, Any], blinding_key: str) -> dict[str, Any]:
    mapping = _blind_mapping(str(record["edge_id"]), blinding_key)
    context = dict(record.get("review_context", {}))
    successor = context.get("successor")
    if isinstance(successor, Mapping) and successor.get("first_valid_time", "") > record["evaluation_cutoff"]:
        context.pop("successor", None)
    card = {
        "schema": "ovc-c2p2-scientific-discrimination-blind-review-card/v1",
        "review_case_id": _hash({
            "schema": "ovc-c2p2-sd-review-case/v1",
            "edge_id": record["edge_id"],
            "disagreement_signature": record["disagreement_signature"],
            "stratum": record["stratum"],
        }),
        "stratum": dict(record["stratum"]),
        "first_valid_time": record["first_valid_time"],
        "evaluation_cutoff": record["evaluation_cutoff"],
        "prior_source_record_id": record["prior_source_record_id"],
        "current_source_record_id": record["current_source_record_id"],
        "candidate_disposition_slots": {slot: record["candidate_dispositions"][candidate_id] for slot, candidate_id in mapping.items()},
        "confirmed_hard_breaks": list(record["confirmed_hard_breaks"]),
        "owner_constitution_evidence": dict(record.get("owner_constitution_evidence", {})),
        "context": context,
        "allowed_labels": ["SAME", "DIFFERENT", "AMBIGUOUS", "NOT_EVALUABLE"],
        "adjudication_label": None,
        "candidate_names_hidden": True,
        "future_information_forbidden": True,
    }
    encoded = _canonical_json(card)
    if any(forbidden in encoded for forbidden in CANDIDATE_IDS):
        raise ScientificDiscriminationError("SD_BLIND_CARD_CANDIDATE_ID_LEAK")
    if any(field in card for field in FORBIDDEN_REVIEW_FIELDS):
        raise ScientificDiscriminationError("SD_BLIND_CARD_FORBIDDEN_FIELD")
    return card


def build_unblinding_map(record: Mapping[str, Any], blinding_key: str) -> dict[str, Any]:
    """Derive the mapping after GADJ label freeze; callers must not emit it beforehand."""
    return {
        "review_case_id": build_blind_review_card(record, blinding_key)["review_case_id"],
        "candidate_slot_map": _blind_mapping(str(record["edge_id"]), blinding_key),
        "release_condition": "ONLY_AFTER_C2P2_SD_GADJ_LABEL_FREEZE",
    }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_streaming_discrimination(
    edges: Iterable[Mapping[str, Any]],
    *,
    output_dir: str | Path,
    blinding_key: str,
) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    ledger_path = root / "disagreement-ledger.jsonl"
    review_path = root / "blind-review-manifest.jsonl"
    database_path = root / "review-selection.sqlite3"
    if any(path.exists() for path in (ledger_path, review_path, database_path)):
        raise ScientificDiscriminationError("SD_OUTPUT_DIR_NOT_EMPTY")

    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        PRAGMA journal_mode=DELETE;
        PRAGMA synchronous=NORMAL;
        CREATE TABLE seen(edge_id TEXT PRIMARY KEY);
        CREATE TABLE representatives(
            selector_key TEXT PRIMARY KEY,
            rank_hash TEXT NOT NULL,
            edge_id TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE hard_cases(
            edge_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL
        );
        """
    )

    total_edges = 0
    disagreement_rows = 0
    hard_rows = 0
    hard_falsification_counts = {candidate_id: 0 for candidate_id in CANDIDATE_IDS}
    with ledger_path.open("w", encoding="utf-8", newline="\n") as ledger:
        for edge in edges:
            record = analyze_edge(edge)
            total_edges += 1
            try:
                connection.execute("INSERT INTO seen(edge_id) VALUES (?)", (record["edge_id"],))
            except sqlite3.IntegrityError as exc:
                raise ScientificDiscriminationError("SD_DUPLICATE_EDGE_ID") from exc
            if not record["include_in_disagreement_ledger"]:
                continue
            disagreement_rows += 1
            payload = _canonical_json(record)
            ledger.write(payload + "\n")
            for candidate_id in record["hard_falsification_candidate_ids"]:
                hard_falsification_counts[candidate_id] += 1
            if record["confirmed_hard_breaks"]:
                hard_rows += 1
                connection.execute(
                    "INSERT INTO hard_cases(edge_id, payload_json) VALUES (?, ?)",
                    (record["edge_id"], payload),
                )
            selector_material = {
                "signature": record["disagreement_signature"],
                "stratum": record["stratum"],
            }
            selector_key = _hash(selector_material)
            rank_hash = sha256(str(record["edge_id"]).encode()).hexdigest()
            existing = connection.execute(
                "SELECT rank_hash FROM representatives WHERE selector_key = ?", (selector_key,)
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO representatives(selector_key, rank_hash, edge_id, payload_json) VALUES (?, ?, ?, ?)",
                    (selector_key, rank_hash, record["edge_id"], payload),
                )
            elif rank_hash < existing[0]:
                connection.execute(
                    "UPDATE representatives SET rank_hash = ?, edge_id = ?, payload_json = ? WHERE selector_key = ?",
                    (rank_hash, record["edge_id"], payload, selector_key),
                )
            if total_edges % 4096 == 0:
                connection.commit()
    connection.commit()

    review_rows = 0
    with review_path.open("w", encoding="utf-8", newline="\n") as review:
        cursor = connection.execute(
            """
            SELECT edge_id, payload_json FROM hard_cases
            UNION ALL
            SELECT r.edge_id, r.payload_json
            FROM representatives r
            WHERE NOT EXISTS (SELECT 1 FROM hard_cases h WHERE h.edge_id = r.edge_id)
            ORDER BY edge_id
            """
        )
        for _, payload_json in cursor:
            record = json.loads(payload_json)
            review.write(_canonical_json(build_blind_review_card(record, blinding_key)) + "\n")
            review_rows += 1

    representative_rows = connection.execute("SELECT COUNT(*) FROM representatives").fetchone()[0]
    database_bytes = database_path.stat().st_size
    connection.close()

    return {
        "schema": "ovc-c2p2-scientific-discrimination-streaming-summary/v1",
        "programme_id": PROGRAMME_ID,
        "total_edges": total_edges,
        "disagreement_ledger_rows": disagreement_rows,
        "confirmed_hard_break_rows": hard_rows,
        "representative_selector_rows": representative_rows,
        "blind_review_rows": review_rows,
        "hard_falsification_counts": hard_falsification_counts,
        "ledger_sha256": _file_sha256(ledger_path),
        "blind_review_manifest_sha256": _file_sha256(review_path),
        "review_selection_database_bytes": database_bytes,
        "candidate_names_in_review_manifest": False,
        "unblinding_map_emitted": False,
        "selection_state": "COMPARATIVE_SET_ONLY_NO_WINNER",
        "c2p_activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "authority_effect": "NONE_TOOLING_ONLY",
    }
