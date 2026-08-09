from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ..application.errors import AuthorityDenied, ContractError
from ..application.guards import deny_validation, require_current_identity, require_read_only
from ..application.models import Availability, Blocker, ConsoleResource, SourceIdentity

_ALLOWED_CLOCKS = {"15M", "2H_A_L"}
_ALLOWED_SIDES = {"BID", "ASK"}
_FORBIDDEN_C2_COMPOSITES = {"confidence_score", "overall_state", "winner_axis"}


class ReadOnlyMappingAdapter:
    resource_type = "GENERIC"
    authority_effect = "NONE_PRESENTATION_ONLY"

    def _identity(self, context: Mapping[str, Any]) -> SourceIdentity:
        commit = require_current_identity(context)
        return SourceIdentity(
            commit=commit,
            release_id=context.get("release_id"),
            contract_ids=tuple(context.get("contract_ids", ())),
            schema_ids=tuple(context.get("schema_ids", ())),
            logical_hashes=tuple(context.get("logical_hashes", ())),
        )

    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        if not isinstance(payload, Mapping) or not isinstance(context, Mapping):
            raise ContractError("MAPPING_SOURCE_REQUIRED")
        require_read_only(payload)
        require_read_only(context)
        identity = self._identity(context)
        return ConsoleResource(
            resource_type=self.resource_type,
            availability=Availability.AVAILABLE,
            authorised=bool(context.get("authorised", False)),
            active=bool(context.get("active", False)),
            authority_effect=str(context.get("authority_effect", self.authority_effect)),
            source_identity=identity,
            payload=deepcopy(dict(payload)),
        )

    def not_materialized(self, context: Mapping[str, Any], *, reason_code: str, owner_programme: str | None = None) -> ConsoleResource:
        require_read_only(context)
        identity = self._identity(context)
        return ConsoleResource(
            resource_type=self.resource_type,
            availability=Availability.NOT_MATERIALIZED,
            authorised=False,
            active=False,
            authority_effect="NONE",
            source_identity=identity,
            payload=None,
            blockers=(Blocker(reason_code=reason_code, owner_programme=owner_programme),),
        )


class ConsoleC1SourceAdapter(ReadOnlyMappingAdapter):
    resource_type = "C1_FACT"

    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        deny_validation(context)
        if str(context.get("clock", "")) not in _ALLOWED_CLOCKS:
            raise ContractError("C1_CLOCK_DENIED")
        if str(context.get("side", "")) not in _ALLOWED_SIDES:
            raise ContractError("C1_SIDE_DENIED")
        if not context.get("release_id"):
            raise ContractError("C1_RELEASE_ID_REQUIRED")
        return super().project(payload, context)


class ConsoleC2SourceAdapter(ReadOnlyMappingAdapter):
    resource_type = "C2_STATE"

    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        deny_validation(context)
        collisions = sorted(_FORBIDDEN_C2_COMPOSITES.intersection(payload))
        if collisions:
            raise ContractError(f"C2_COMPOSITE_STATE_FORBIDDEN:{collisions}")
        axes = payload.get("axes")
        if axes is not None and not isinstance(axes, Mapping):
            raise ContractError("C2_AXES_MAPPING_REQUIRED")
        return super().project(payload, context)


class ConsoleC2ESourceAdapter(ReadOnlyMappingAdapter):
    resource_type = "C2E_EPISODE"

    def project_optional(self, payload: Mapping[str, Any] | None, context: Mapping[str, Any]) -> ConsoleResource:
        deny_validation(context)
        if payload is None:
            return self.not_materialized(
                context,
                reason_code="C2E_CURRENT_GENERATION_NOT_MATERIALIZED",
                owner_programme="OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2",
            )
        generation = str(payload.get("generation", ""))
        schema = str(payload.get("schema", ""))
        if generation not in {"C2E_V0_2", "C2E2"} and "c2e" not in schema.lower():
            raise ContractError("C2E_CURRENT_GENERATION_REQUIRED")
        return super().project(payload, context)


class OccurrenceContextSourceAdapter(ReadOnlyMappingAdapter):
    resource_type = "OCCURRENCE_CONTEXT"

    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        if payload.get("rewrite_structural_identity") is True or payload.get("structural_identity_override"):
            raise AuthorityDenied("OCCURRENCE_CONTEXT_STRUCTURAL_IDENTITY_MUTATION_DENIED")
        if not payload.get("occurrence_id") or not payload.get("context_id"):
            raise ContractError("OCCURRENCE_CONTEXT_IDENTITY_REQUIRED")
        return super().project(payload, context)


class SFCSourceAdapter(ReadOnlyMappingAdapter):
    resource_type = "SFC_FAMILY_EVIDENCE"

    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        if context.get("method_authority") not in {None, "NONE"}:
            raise AuthorityDenied("SFC_METHOD_AUTHORITY_NOT_GRANTED_TO_CONSOLE")
        return super().project(payload, context)


class ResearchOperationsSourceAdapter(ReadOnlyMappingAdapter):
    resource_type = "RESEARCH_OPERATIONS"

    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        if bool(context.get("authoritative_index", False)):
            raise AuthorityDenied("RESEARCH_OPERATIONS_INDEX_MUST_REMAIN_REPLACEABLE")
        return super().project(payload, context)


class GovernanceSourceAdapter(ReadOnlyMappingAdapter):
    resource_type = "GOVERNANCE_READ"

    def project(self, payload: Mapping[str, Any], context: Mapping[str, Any]) -> ConsoleResource:
        source_kind = str(context.get("source_kind", ""))
        if source_kind == "GRT":
            allowed = {"NONE_DERIVED_REPLACEABLE_READ_MODEL", "NONE_PRESENTATION_ONLY", "NONE"}
            if str(payload.get("authority_effect", context.get("authority_effect", "NONE"))) not in allowed:
                raise AuthorityDenied("GRT_AUTHORITY_BOUNDARY_MISMATCH")
        elif source_kind == "IROF":
            if bool(context.get("orchestration_commands_enabled", False)):
                raise AuthorityDenied("IROF_COMMAND_AUTHORITY_DENIED")
        else:
            raise AuthorityDenied("GOVERNANCE_SOURCE_KIND_DENIED")
        return super().project(payload, context)
