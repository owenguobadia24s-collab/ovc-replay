from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from ovc.research_operations.canonical import canonical_json_bytes
from ovc.research_operations.config import ResearchOperationsConfig
from ovc.research_operations.storage import DraftStore, FrozenRecordStore, ResearchWriteService

from .annotation_friction_service import (
    ALLOWED_ANNOTATIONS,
    ALLOWED_FRICTION_REASONS,
    ALLOWED_MODES,
    RO4AnnotationFrictionService,
    RO4AppendAuthority,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _emit(value: Any) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(value))


def _json(value: str) -> Any:
    return json.loads(value)


def _service(repo_root: str | None) -> RO4AnnotationFrictionService:
    config = ResearchOperationsConfig.from_environment(repository_root=repo_root)
    writes = ResearchWriteService(
        drafts=DraftStore(config.runtime_root / "drafts"),
        records=FrozenRecordStore(config.record_root),
        operator_id=config.operator_id,
    )
    registry = config.repository_root / "registries" / "research_operations" / "v0_4" / "RO4_APPEND_AUTHORITY_v0_1.json"
    return RO4AnnotationFrictionService(writes=writes, authority=RO4AppendAuthority.from_registry(registry))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ovc ro4", description="Governed RO4 annotation/friction service")
    parser.add_argument("--repo-root", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    annotation = sub.add_parser("annotate-boundary")
    annotation.add_argument("--sequence", required=True)
    annotation.add_argument("--release", required=True)
    annotation.add_argument("--manifest-sha256", required=True)
    annotation.add_argument("--clock", required=True, choices=["15M", "2H_A_L"])
    annotation.add_argument("--side", required=True, choices=["BID", "ASK"])
    annotation.add_argument("--member-id", action="append", required=True)
    annotation.add_argument("--member-first-valid", action="append", required=True)
    annotation.add_argument("--mode", required=True, choices=sorted(ALLOWED_MODES))
    annotation.add_argument("--cutoff", required=True)
    annotation.add_argument("--annotation", required=True, choices=sorted(ALLOWED_ANNOTATIONS))
    annotation.add_argument("--rationale", required=True)
    annotation.add_argument("--at", default=None)

    friction = sub.add_parser("record-friction")
    friction.add_argument("--sequence", required=True)
    friction.add_argument("--release", required=True)
    friction.add_argument("--source-first-valid", action="append", required=True)
    friction.add_argument("--mode", required=True, choices=sorted(ALLOWED_MODES))
    friction.add_argument("--cutoff", required=True)
    friction.add_argument("--reason", required=True, choices=sorted(ALLOWED_FRICTION_REASONS))
    friction.add_argument("--evidence-ref", action="append", required=True)
    friction.add_argument("--counterexample-ref", action="append", default=[])
    friction.add_argument("--remediation-ref", default=None)
    friction.add_argument("--rationale", default="")
    friction.add_argument("--at", default=None)

    review = sub.add_parser("review-sequence")
    review.add_argument("--sequence", required=True)
    review.add_argument("--source-release-and-manifest", required=True, help="JSON object")
    review.add_argument("--mode", required=True, choices=sorted(ALLOWED_MODES))
    review.add_argument("--cutoff", required=True)
    review.add_argument("--admissible", required=True, help="JSON object")
    review.add_argument("--post-cutoff-hidden-count", type=int, required=True)
    review.add_argument("--logical-hash", required=True)
    review.add_argument("--source-first-valid", action="append", required=True)
    review.add_argument("--at", default=None)

    supersede = sub.add_parser("supersede")
    supersede.add_argument("--record", required=True)
    supersede.add_argument("--replacement", required=True, help="Complete DRAFT envelope JSON or @file")
    supersede.add_argument("--at", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        service = _service(args.repo_root)
        at = args.at or _utc_now()
        if args.command == "annotate-boundary":
            result = service.append_boundary_annotation(
                source_sequence_id=args.sequence,
                source_release_id=args.release,
                manifest_sha256=args.manifest_sha256,
                clock=args.clock,
                side=args.side,
                member_ids=args.member_id,
                member_first_valid_times=args.member_first_valid,
                operation_mode=args.mode,
                admissible_cutoff=args.cutoff,
                annotation=args.annotation,
                rationale=args.rationale,
                frozen_at=at,
            )
        elif args.command == "record-friction":
            result = service.append_friction_record(
                source_sequence_id=args.sequence,
                source_release_id=args.release,
                source_first_valid_times=args.source_first_valid,
                operation_mode=args.mode,
                admissible_cutoff=args.cutoff,
                reason_code=args.reason,
                evidence_refs=args.evidence_ref,
                counterexample_refs=args.counterexample_ref,
                remediation_ref=args.remediation_ref,
                rationale=args.rationale,
                frozen_at=at,
            )
        elif args.command == "review-sequence":
            result = service.append_prospective_review(
                source_sequence_id=args.sequence,
                source_release_and_manifest=_json(args.source_release_and_manifest),
                operation_mode=args.mode,
                admissible_cutoff=args.cutoff,
                admissible=_json(args.admissible),
                post_cutoff_hidden_count=args.post_cutoff_hidden_count,
                logical_hash=args.logical_hash,
                source_first_valid_times=args.source_first_valid,
                frozen_at=at,
            )
        else:
            replacement_text = Path(args.replacement[1:]).read_text(encoding="utf-8") if args.replacement.startswith("@") else args.replacement
            result = service.supersede(args.record, _json(replacement_text), frozen_at=at)
        _emit({"status": "PASS", "record": result})
        return 0
    except Exception as exc:
        _emit({"status": "BLOCK", "error_type": type(exc).__name__, "message": str(exc)})
        return 2
