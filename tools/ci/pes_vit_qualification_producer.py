from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

from ovc.development.skills.pes.vit_qualification_producer import (
    validate_qualification_publication_request,
)
from tools.ci.vit_qualification_store import build_qualification_envelope


def _load_canonical_object(path: Path) -> Mapping[str, object]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"PES_VIT_PRODUCER_REQUEST_INVALID_JSON:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError("PES_VIT_PRODUCER_REQUEST_INVALID_OBJECT")
    canonical = json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if raw != canonical:
        raise RuntimeError("PES_VIT_PRODUCER_REQUEST_NOT_CANONICAL_JSON")
    return value


def prepare_shadow_envelope(
    *,
    repo: Path,
    request: Mapping[str, object],
    expected_issuer_identity: str,
) -> Mapping[str, object]:
    validated = validate_qualification_publication_request(
        request,
        expected_issuer_identity=expected_issuer_identity,
    )
    envelope = build_qualification_envelope(
        root=repo,
        head_sha=validated.candidate_head_sha,
        lineage_record=validated.lineage_record,
    )
    if str(envelope.get("pip_id", "")) != validated.pip_id:
        raise RuntimeError("PES_VIT_PRODUCER_ENVELOPE_PIP_MISMATCH")
    if str(envelope.get("authority_manifest_id", "")) != validated.authority_manifest_id:
        raise RuntimeError("PES_VIT_PRODUCER_ENVELOPE_AUTHORITY_MISMATCH")
    if str(envelope.get("dependency_frontier_id", "")) != validated.dependency_frontier_id:
        raise RuntimeError("PES_VIT_PRODUCER_ENVELOPE_FRONTIER_MISMATCH")
    return envelope


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a detached exact-head VIT qualification envelope from an "
            "already-authorised durable owner request. This WP1 tool is shadow-only "
            "and cannot publish to the ledger."
        )
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--expected-issuer-identity", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    request = _load_canonical_object(Path(args.request_json).resolve())
    envelope = prepare_shadow_envelope(
        repo=repo,
        request=request,
        expected_issuer_identity=args.expected_issuer_identity,
    )
    print(json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("PES_VIT_QUALIFICATION_PRODUCER=SHADOW_READY_NO_LEDGER_WRITE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
