from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

from ovc.development.skills.pes_vit_qualification_producer import (
    validate_producer_activation,
    validate_producer_dispatch,
    validate_qualification_publication_request,
)
from ovc.development.skills.repository_assurance_pilot import (
    is_pilot_receipt_path,
    load_json,
    validate_pilot_policy,
)
from tools.ci.vit_qualification_store import (
    build_qualification_envelope,
    publish_qualification_envelope,
)


SELECTED_CLASS_ROUTE = Path("registries/development/skills/VIT_SELECTED_CLASS_ROUTE_v0_1.json")
PILOT_POLICY = Path("registries/development/skills/REPOSITORY_ASSURANCE_PILOT_POLICY_v0_1.json")


def _reject_diasi_selected_class_old_route(
    *,
    repo: Path,
    request: Mapping[str, object],
) -> None:
    """Fence the exact class transferred to its owner-local generation-2 writer."""
    route = load_json(repo / SELECTED_CLASS_ROUTE)
    policy = validate_pilot_policy(load_json(repo / PILOT_POLICY))
    lineage = request.get("lineage")
    if not isinstance(lineage, Mapping):
        return
    pip = lineage.get("pip")
    if not isinstance(pip, Mapping):
        return
    changes = pip.get("logical_changes")
    if not isinstance(changes, list) or not changes:
        return
    exact_selected_class = all(
        isinstance(change, Mapping)
        and str(change.get("op", "")) in policy["allowed_ops"]
        and is_pilot_receipt_path(str(change.get("path", "")), policy)
        for change in changes
    )
    if not exact_selected_class:
        return
    pre_removal_fence = (
        route.get("schema") == "ovc-diasi-selected-class-live-route/v1"
        and route.get("status") == "ACTIVE_REFERENCE_ASSURED"
        and route.get("route_generation") == 2
        and route.get("old_route") == "DISABLED_RETAINED"
    )
    post_removal_fence = (
        route.get("schema") == "ovc-diasi-selected-class-live-route/v2"
        and route.get("status") == "ACTIVE_RETIREMENT_COMPLETE"
        and route.get("route_generation") == 3
        and "old_route" not in route
    )
    if (
        route.get("selected_class") != policy["pilot_class"]
        or route.get("qualification_writer") != "VIT_QUALIFICATION_OWNER_LOCAL"
        or not (pre_removal_fence or post_removal_fence)
    ):
        raise RuntimeError("PES_VIT_PRODUCER_DIASI_SELECTED_CLASS_ROUTE_STATE_DRIFT")
    raise RuntimeError("PES_VIT_PRODUCER_DIASI_SELECTED_CLASS_OLD_ROUTE_FENCED")


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
    _reject_diasi_selected_class_old_route(repo=repo, request=request)
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


def publish_authorised_request(
    *,
    repo: Path,
    request: Mapping[str, object],
    activation: Mapping[str, object],
    dispatch: Mapping[str, object],
    expected_issuer_identity: str,
    expected_fencing_generation: int,
) -> Mapping[str, object]:
    validated_request = validate_qualification_publication_request(
        request,
        expected_issuer_identity=expected_issuer_identity,
    )
    validated_activation = validate_producer_activation(activation)
    validated_dispatch = validate_producer_dispatch(
        dispatch,
        request=validated_request,
        activation=validated_activation,
        expected_fencing_generation=expected_fencing_generation,
    )
    envelope = prepare_shadow_envelope(
        repo=repo,
        request=request,
        expected_issuer_identity=expected_issuer_identity,
    )
    qualification_id = publish_qualification_envelope(envelope)
    if qualification_id != str(envelope.get("qualification_id", "")):
        raise RuntimeError("PES_VIT_PRODUCER_PUBLISH_ID_MISMATCH")
    return {
        "status": "PUBLISHED_OR_IDEMPOTENTLY_REUSED",
        "request_id": validated_request.request_id,
        "dispatch_id": validated_dispatch.dispatch_id,
        "activation_id": validated_activation.activation_id,
        "qualification_id": qualification_id,
        "candidate_head_sha": validated_request.candidate_head_sha,
        "ledger_branch": validated_activation.ledger_branch,
        "ledger_root": validated_activation.ledger_root,
        "write_scope": validated_activation.write_scope,
        "authority_effect": "NONE_EXECUTE_AUTHORISED_OWNER_REQUEST",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or, after the exact operator activation grant, publish a detached "
            "exact-head VIT qualification envelope from an already-authorised durable "
            "owner request. Publish mode is ledger-ref-only and requires an exact "
            "PES fencing-bound dispatch."
        )
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--expected-issuer-identity", required=True)
    parser.add_argument("--mode", choices=("shadow", "publish"), default="shadow")
    parser.add_argument("--activation-json")
    parser.add_argument("--dispatch-json")
    parser.add_argument("--expected-fencing-generation", type=int)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    request = _load_canonical_object(Path(args.request_json).resolve())

    if args.mode == "shadow":
        envelope = prepare_shadow_envelope(
            repo=repo,
            request=request,
            expected_issuer_identity=args.expected_issuer_identity,
        )
        print(
            json.dumps(
                envelope,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        )
        print("PES_VIT_QUALIFICATION_PRODUCER=SHADOW_READY_NO_LEDGER_WRITE")
        return 0

    if not args.activation_json or not args.dispatch_json:
        raise RuntimeError("PES_VIT_PRODUCER_PUBLISH_REQUIRES_ACTIVATION_AND_DISPATCH")
    if args.expected_fencing_generation is None:
        raise RuntimeError("PES_VIT_PRODUCER_PUBLISH_REQUIRES_FENCING_GENERATION")

    activation_packet = _load_canonical_object(Path(args.activation_json).resolve())
    runtime_activation = activation_packet.get("runtime_activation")
    if not isinstance(runtime_activation, Mapping):
        raise RuntimeError("PES_VIT_PRODUCER_RUNTIME_ACTIVATION_MISSING")
    dispatch = _load_canonical_object(Path(args.dispatch_json).resolve())
    result = publish_authorised_request(
        repo=repo,
        request=request,
        activation=runtime_activation,
        dispatch=dispatch,
        expected_issuer_identity=args.expected_issuer_identity,
        expected_fencing_generation=args.expected_fencing_generation,
    )
    print(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )
    print("PES_VIT_QUALIFICATION_PRODUCER=ACTIVE_LEDGER_PUBLICATION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
