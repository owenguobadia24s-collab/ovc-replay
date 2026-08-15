from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from .adjudication import prove_retrieval_superset, reference_retrieve
from .canonical import canonical_bytes


def _key(record: Mapping[str, Any]) -> bytes:
    return canonical_bytes(
        {
            "object_pack_id": record.get("object_pack_id"),
            "structural_role_id": record.get("structural_role_id"),
            "geometry_kind_id": record.get("geometry_kind_id"),
            "hard_scope": record.get("hard_scope"),
        }
    )


@dataclass(frozen=True)
class ExactHardScopeIndex:
    buckets: Mapping[bytes, tuple[Mapping[str, Any], ...]]
    index_digest: str

    @classmethod
    def build(cls, assertions: Sequence[Mapping[str, Any]]) -> "ExactHardScopeIndex":
        mutable: dict[bytes, list[Mapping[str, Any]]] = {}
        for assertion in assertions:
            mutable.setdefault(_key(assertion), []).append(dict(assertion))
        buckets = {
            key: tuple(sorted(values, key=lambda item: item["object_assertion_id"]))
            for key, values in mutable.items()
        }
        digest_payload = [
            {
                "key_sha256": sha256(key).hexdigest(),
                "assertion_ids": [item["object_assertion_id"] for item in values],
            }
            for key, values in sorted(buckets.items(), key=lambda item: item[0])
        ]
        digest = sha256(canonical_bytes(digest_payload)).hexdigest()
        return cls(buckets=buckets, index_digest=digest)

    def retrieve(self, candidate: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
        return self.buckets.get(_key(candidate), ())


def static_retrieval_equivalence_contract() -> Mapping[str, Any]:
    return {
        "schema": "c2p-optimized-retrieval-static-proof/v0.2",
        "reference_scope_fields": [
            "object_pack_id",
            "structural_role_id",
            "geometry_kind_id",
            "hard_scope",
        ],
        "optimized_key_fields": [
            "object_pack_id",
            "structural_role_id",
            "geometry_kind_id",
            "hard_scope",
        ],
        "authority": "NON_AUTHORITATIVE_RETRIEVAL_ONLY",
        "false_negative_policy": "FAIL_CLOSED",
    }


def prove_dynamic_retrieval_equivalence(
    candidate: Mapping[str, Any],
    assertions: Sequence[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    index: ExactHardScopeIndex,
) -> Mapping[str, Any]:
    query_id, reference = reference_retrieve(candidate, assertions, object_pack)
    optimized = list(index.retrieve(candidate))
    reference_ids = [item["object_assertion_id"] for item in reference]
    optimized_ids = [item["object_assertion_id"] for item in optimized]
    prove_retrieval_superset(reference_ids, optimized_ids)
    if reference_ids != optimized_ids:
        raise ValueError("C2P_OPTIMIZED_RETRIEVAL_NOT_EXACT")
    return {
        "schema": "c2p-optimized-retrieval-dynamic-proof/v0.2",
        "retrieval_query_id": query_id,
        "index_digest": index.index_digest,
        "reference_assertion_ids": reference_ids,
        "optimized_assertion_ids": optimized_ids,
        "result": "PASS_EXACT_EQUIVALENCE",
    }
