from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .canonical import canonical_json_bytes
from .catalogue import ArtifactCatalogueBuilder, catalogue_report, read_catalogue, write_catalogue
from .config import ResearchOperationsConfig
from .operations import ResearchOperationsService
from .paths import ApprovedPathRegistry
from .queues import ResearchQueueService
from .storage import DraftStore, FrozenRecordStore, ResearchWriteService


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_value(value: str, registry: ApprovedPathRegistry | None = None) -> Any:
    if value.startswith("@"):
        if registry is None or ":" not in value[1:]:
            raise ValueError("file inputs use @root_alias:relative/path.json")
        alias, relative = value[1:].split(":", 1)
        path = registry.resolve(alias, relative, must_exist=True)
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _emit(value: Any) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(value))


def _runtime(args: argparse.Namespace):
    config = ResearchOperationsConfig.from_environment(repository_root=args.repo_root)
    drafts = DraftStore(config.runtime_root / "drafts")
    records = FrozenRecordStore(config.record_root)
    writes = ResearchWriteService(drafts=drafts, records=records, operator_id=config.operator_id)
    service = ResearchOperationsService(writes)
    registry_path = config.repository_root / "registries" / "research_operations" / "RESEARCH_OPERATIONS_PATH_REGISTRY_v0_1.json"
    registry = ApprovedPathRegistry.from_json(registry_path, config)
    return config, drafts, records, writes, service, registry


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", default=None, help="Repository root; otherwise OVC_REPOSITORY_ROOT or cwd")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ovc", description="Governed OVC Research Operations CLI")
    _add_common(parser)
    root = parser.add_subparsers(dest="domain", required=True)

    research = root.add_parser("research")
    research_sub = research.add_subparsers(dest="research_command", required=True)

    open_session = research_sub.add_parser("open-session")
    open_session.add_argument("--instrument", required=True)
    open_session.add_argument("--release", required=True)
    open_session.add_argument("--role", required=True, choices=["DISCOVERY", "DEVELOPMENT", "VALIDATION_METADATA_ONLY"])
    open_session.add_argument("--cutoff", required=True)
    open_session.add_argument("--objective", required=True)
    open_session.add_argument("--at", default=None)

    add_observation = research_sub.add_parser("add-observation")
    add_observation.add_argument("--session", required=True)
    add_observation.add_argument("--release", required=True)
    add_observation.add_argument("--cutoff", required=True)
    add_observation.add_argument("--visible-facts", required=True, help="JSON object or @root_alias:relative/path.json")
    add_observation.add_argument("--unknown", action="append", default=[])
    add_observation.add_argument("--source-record-ref", action="append", default=[])
    add_observation.add_argument("--model-refs", default="[]", help="JSON array or @root_alias:relative/path.json")
    add_observation.add_argument("--artifact-refs", default="[]", help="JSON array or @root_alias:relative/path.json")
    add_observation.add_argument("--at", default=None)

    freeze_observation = research_sub.add_parser("freeze-observation")
    freeze_observation.add_argument("--draft", required=True)
    freeze_observation.add_argument("--at", default=None)

    freeze_claim = research_sub.add_parser("freeze-claim")
    freeze_claim.add_argument("--observation", required=True)
    freeze_claim.add_argument("--release", required=True)
    freeze_claim.add_argument("--cutoff", required=True)
    freeze_claim.add_argument("--eligibility", required=True, help="JSON value or @root_alias:relative/path.json")
    freeze_claim.add_argument("--discriminator", required=True, help="JSON value or @root_alias:relative/path.json")
    freeze_claim.add_argument("--falsifier", required=True, help="JSON value or @root_alias:relative/path.json")
    freeze_claim.add_argument("--horizons", required=True, help="JSON array or @root_alias:relative/path.json")
    freeze_claim.add_argument("--at", default=None)

    realization = research_sub.add_parser("register-realization")
    realization.add_argument("--observation", required=True)
    realization.add_argument("--claim", default=None)
    realization.add_argument("--release", required=True)
    realization.add_argument("--cutoff", required=True)
    realization.add_argument("--reference-time", required=True)
    realization.add_argument("--horizon", required=True)
    realization.add_argument("--coverage", required=True, help="JSON value or @root_alias:relative/path.json")
    realization.add_argument("--path", required=True, help="JSON value or @root_alias:relative/path.json")
    realization.add_argument("--censoring-state", required=True)
    realization.add_argument("--at", default=None)

    adjudicate = research_sub.add_parser("adjudicate")
    adjudicate.add_argument("--observation", required=True)
    adjudicate.add_argument("--claim", required=True)
    adjudicate.add_argument("--realization", required=True)
    adjudicate.add_argument("--release", required=True)
    adjudicate.add_argument("--cutoff", required=True)
    adjudicate.add_argument("--evidence-role", required=True)
    adjudicate.add_argument("--admissibility", required=True)
    adjudicate.add_argument("--at", default=None)

    close_session = research_sub.add_parser("close-session")
    close_session.add_argument("--session", required=True, help="Session draft ID")
    close_session.add_argument("--incident", action="append", default=[])
    close_session.add_argument("--unresolved", action="append", default=[])
    close_session.add_argument("--next-action", required=True)
    close_session.add_argument("--at", default=None)

    supersede = research_sub.add_parser("supersede")
    supersede.add_argument("--record", required=True)
    supersede.add_argument("--replacement", required=True, help="Replacement DRAFT JSON or @root_alias:relative/path.json")
    supersede.add_argument("--at", default=None)

    artifact = root.add_parser("artifact")
    artifact_sub = artifact.add_subparsers(dest="artifact_command", required=True)

    scan = artifact_sub.add_parser("scan")
    scan.add_argument("--root-alias", action="append", required=True)
    scan.add_argument("--source-commit", default=None)
    scan.add_argument("--at", default=None)

    verify = artifact_sub.add_parser("verify")
    verify.add_argument("--declarations-root", required=True)
    verify.add_argument("--declarations-path", required=True)
    verify.add_argument("--source-commit", default=None)
    verify.add_argument("--at", default=None)

    artifact_sub.add_parser("report")

    queue = root.add_parser("queue")
    queue_sub = queue.add_subparsers(dest="queue_command", required=True)
    show = queue_sub.add_parser("show")
    show.add_argument("--type", required=True, choices=["realization-due", "open-incidents", "incomplete-sessions", "stale-catalogues", "missing-artifacts"])
    show.add_argument("--as-of", default=None)
    show.add_argument("--stale-after-hours", type=int, default=24)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        config, drafts, records, writes, service, registry = _runtime(args)
        at = getattr(args, "at", None) or getattr(args, "as_of", None) or _utc_now()

        if args.domain == "research":
            if args.research_command == "open-session":
                draft_id = service.open_session(instrument=args.instrument, release_id=args.release, role=args.role, cutoff=args.cutoff, objective=args.objective, created_at=at)
                _emit({"status": "PASS", "draft_id": draft_id})
            elif args.research_command == "add-observation":
                draft_id = service.add_observation(
                    session_id=args.session,
                    release_id=args.release,
                    cutoff=args.cutoff,
                    visible_facts=_json_value(args.visible_facts, registry),
                    unknowns=args.unknown,
                    source_record_refs=args.source_record_ref,
                    model_refs=_json_value(args.model_refs, registry),
                    artifact_refs=_json_value(args.artifact_refs, registry),
                    created_at=at,
                )
                _emit({"status": "PASS", "draft_id": draft_id})
            elif args.research_command == "freeze-observation":
                _emit(service.freeze_observation(draft_id=args.draft, frozen_at=at))
            elif args.research_command == "freeze-claim":
                _emit(service.freeze_claim(
                    observation_id=args.observation,
                    release_id=args.release,
                    cutoff=args.cutoff,
                    eligibility=_json_value(args.eligibility, registry),
                    discriminator=_json_value(args.discriminator, registry),
                    falsifier=_json_value(args.falsifier, registry),
                    horizons=_json_value(args.horizons, registry),
                    frozen_at=at,
                ))
            elif args.research_command == "register-realization":
                _emit(service.register_realization(
                    observation_id=args.observation,
                    claim_id=args.claim,
                    release_id=args.release,
                    cutoff=args.cutoff,
                    reference_time=args.reference_time,
                    horizon=args.horizon,
                    coverage=_json_value(args.coverage, registry),
                    path=_json_value(args.path, registry),
                    censoring_state=args.censoring_state,
                    frozen_at=at,
                ))
            elif args.research_command == "adjudicate":
                _emit(service.adjudicate(
                    observation_id=args.observation,
                    claim_id=args.claim,
                    realization_id=args.realization,
                    release_id=args.release,
                    cutoff=args.cutoff,
                    evidence_role=args.evidence_role,
                    admissibility=args.admissibility,
                    frozen_at=at,
                ))
            elif args.research_command == "close-session":
                _emit(service.close_session(
                    draft_id=args.session,
                    incidents=args.incident,
                    unresolved_questions=args.unresolved,
                    next_action=args.next_action,
                    frozen_at=at,
                ))
            elif args.research_command == "supersede":
                replacement = _json_value(args.replacement, registry)
                _emit(writes.supersede(args.record, replacement, frozen_at=at))
            return 0

        catalogue_path = config.runtime_root / "catalogue" / "current.json"
        if args.domain == "artifact":
            source_commit = getattr(args, "source_commit", None) or os.environ.get("OVC_SOURCE_COMMIT") or "UNRESOLVED"
            builder = ArtifactCatalogueBuilder(registry)
            if args.artifact_command == "scan":
                catalogue = builder.scan(aliases=args.root_alias, generated_at=at, source_commit=source_commit)
                write_catalogue(catalogue_path, catalogue)
                writes.emit_audit(action="artifact.scan", object_id=catalogue.logical_inventory_sha256, result="PASS", trace_ref="runtime:catalogue/current.json", at=at)
                _emit(catalogue.to_dict())
            elif args.artifact_command == "verify":
                declarations_path = registry.resolve(args.declarations_root, args.declarations_path, must_exist=True)
                declarations = json.loads(declarations_path.read_text(encoding="utf-8"))
                if isinstance(declarations, dict):
                    declarations = declarations.get("artifacts", [])
                catalogue = builder.verify_declarations(declarations, generated_at=at, source_commit=source_commit)
                write_catalogue(catalogue_path, catalogue)
                writes.emit_audit(action="artifact.verify", object_id=catalogue.logical_inventory_sha256, result="PASS" if not any(issue.severity == "BLOCK" for issue in catalogue.issues) else "BLOCK", trace_ref="runtime:catalogue/current.json", at=at)
                _emit(catalogue.to_dict())
            elif args.artifact_command == "report":
                _emit(catalogue_report(read_catalogue(catalogue_path)))
            return 0

        if args.domain == "queue" and args.queue_command == "show":
            catalogue = read_catalogue(catalogue_path) if catalogue_path.exists() else None
            queue = ResearchQueueService(records=records, catalogue=catalogue, drafts=drafts)
            _emit({"queue": args.type, "items": queue.show(args.type, as_of=at, stale_after_hours=args.stale_after_hours)})
            return 0

        parser.error("unsupported command")
    except Exception as exc:  # fail closed with typed operator-visible error
        _emit({"status": "BLOCK", "error_type": type(exc).__name__, "message": str(exc)})
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
