from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ovc.research_orchestration.serialization import logical_sha256

from .contracts import MCACContractError

DOCTRINE_ID = "OVC.MCAC.NEGATIVE_DOCTRINE.v0.1"
ASSERTION_IDS = (
    "NO_SHARED_CATEGORICAL_PHASE_LATTICE",
    "NO_IMPLICIT_TV120_NATIVE_TO_2H_A_L_EQUIVALENCE",
    "NESTING_NOT_COMPOSITION",
    "MORPHOLOGY_NOT_IDENTITY",
    "COMMON_GEOMETRY_NEGATIVE_IS_CARRIER_SCOPED",
    "FAILED_CORRESPONDENCE_CHAIN_PRESERVED",
)


def semantic_doctrine() -> dict[str, Any]:
    return {
        "doctrine_id": DOCTRINE_ID,
        "assertions": list(ASSERTION_IDS),
        "effect": "ENFORCEMENT_CONSTRAINTS_NOT_MARKET_SEMANTICS",
        "fresh_scientific_confirmation": "FORBIDDEN",
    }


DOCTRINE_HASH = logical_sha256(semantic_doctrine())


@dataclass(frozen=True)
class DoctrineReceipt:
    doctrine_id: str
    doctrine_hash: str
    enforced_assertions: tuple[str, ...]
    identity_effect: str = "NONE"
    composition_effect: str = "NONE"
    ontology_effect: str = "NONE"


def enforce_doctrine(assertions: Iterable[str], doctrine_hash: str) -> DoctrineReceipt:
    observed = tuple(sorted(set(assertions)))
    if doctrine_hash != DOCTRINE_HASH:
        raise MCACContractError("MCAC_DOCTRINE_HASH_MISMATCH", doctrine_hash)
    missing = tuple(item for item in ASSERTION_IDS if item not in observed)
    if missing:
        raise MCACContractError("MCAC_NEGATIVE_DOCTRINE_MISSING", ",".join(missing))
    return DoctrineReceipt(DOCTRINE_ID, DOCTRINE_HASH, observed)
