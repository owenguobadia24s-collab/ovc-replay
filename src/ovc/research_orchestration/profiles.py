from __future__ import annotations

from .models import PipelineProfile


def builtin_profiles() -> tuple[PipelineProfile, ...]:
    return (
        PipelineProfile("C1_ONLY", "0.1", ("C1",), ("C1_RECORDS",)),
        PipelineProfile("C2_ONLY", "0.1", ("C1", "C2_REVISED"), ("C2_STATE_STREAM",)),
        PipelineProfile("C2_C2E", "0.1", ("C1", "C2_REVISED", "C2E_V0_2"), ("C2E_STREAM",)),
        PipelineProfile("STRUCTURAL_CORE", "0.1", ("C1", "C2_REVISED", "C2E_V0_2", "SRI_REPRESENTATION"), ("REPRESENTATION_POPULATION",)),
        PipelineProfile(
            "FAMILY_RESEARCH",
            "0.1",
            ("C1", "C2_REVISED", "C2E_V0_2", "SRI_REPRESENTATION", "COMPARABILITY_COMPARISON_DISTANCE", "FDI_C2G_FAMILY", "FAMILY_EVIDENCE_STREAM"),
            ("FAMILY_EVIDENCE_STREAM",),
        ),
        PipelineProfile(
            "FULL_DESCRIPTIVE",
            "0.1",
            ("POPULATION_SOURCE_OPT_A", "C1", "C2_REVISED", "C2E_V0_2", "SRI_REPRESENTATION", "COMPARABILITY_COMPARISON_DISTANCE", "FDI_C2G_FAMILY", "FAMILY_EVIDENCE_STREAM", "RESEARCH_OPERATIONS"),
            ("RESEARCH_OPERATIONS_EVIDENCE",),
            allowed_optional_branches=("MCARB_AUXILIARY_BRANCH",),
        ),
        PipelineProfile(
            "FULL_DESCRIPTIVE_WITH_CONTEXT",
            "0.1",
            ("POPULATION_SOURCE_OPT_A", "C1", "C2_REVISED", "C2E_V0_2", "OCCURRENCE_CONTEXT", "SRI_REPRESENTATION", "COMPARABILITY_COMPARISON_DISTANCE", "FDI_C2G_FAMILY", "FAMILY_EVIDENCE_STREAM", "RESEARCH_OPERATIONS"),
            ("RESEARCH_OPERATIONS_EVIDENCE",),
            allowed_optional_branches=("MCARB_AUXILIARY_BRANCH",),
        ),
    )


CURRENT_PROFILES: tuple[PipelineProfile, ...] = builtin_profiles()


def profile_by_id(profile_id: str) -> PipelineProfile:
    matches = [item for item in CURRENT_PROFILES if item.profile_id == profile_id]
    if not matches:
        raise KeyError(profile_id)
    return matches[0]
