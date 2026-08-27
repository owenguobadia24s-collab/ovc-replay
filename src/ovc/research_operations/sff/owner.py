from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .core import AuthorityError, content_identity


@dataclass(frozen=True)
class OwnerFact:
    dependency_id: str
    owner_id: str
    fact_identity: str
    currentness: str
    authority: str

    @property
    def owner_fact_id(self) -> str:
        return content_identity("sff-owner-fact", self)


class OwnerResolver:
    """Read-only exact owner resolution; never reconstructs missing truth."""

    def __init__(self, facts: Iterable[OwnerFact]) -> None:
        grouped: dict[str, list[OwnerFact]] = {}
        for fact in facts:
            grouped.setdefault(fact.dependency_id, []).append(fact)
        self._facts = grouped

    def resolve(self, dependency_id: str) -> OwnerFact:
        matches = self._facts.get(dependency_id, [])
        if not matches:
            raise AuthorityError(f"OWNER_FACT_MISSING:{dependency_id}")
        identities = {fact.owner_fact_id for fact in matches}
        if len(identities) != 1:
            raise AuthorityError(f"OWNER_FACT_CONFLICT:{dependency_id}")
        fact = matches[0]
        if fact.currentness != "CURRENT":
            raise AuthorityError(f"OWNER_FACT_STALE:{dependency_id}")
        if fact.authority != "AUTHORIZED_READ_ONLY":
            raise AuthorityError(f"OWNER_FACT_UNAUTHORIZED:{dependency_id}")
        return fact

    def resolve_all(self, dependencies: Iterable[str]) -> tuple[OwnerFact, ...]:
        return tuple(self.resolve(dependency) for dependency in dependencies)
