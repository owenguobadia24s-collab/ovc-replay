from __future__ import annotations

from copy import deepcopy
from typing import Any

from .storage import ResearchWriteService


class ResearchOperationsService:
    def __init__(self, writes: ResearchWriteService):
        self.writes = writes

    def open_session(
        self,
        *,
        instrument: str,
        release_id: str,
        role: str,
        cutoff: str,
        objective: str,
        created_at: str,
    ) -> str:
        ref = self.writes.release_ref(release_id, cutoff)
        draft = self.writes.base_record(
            record_type="RESEARCH_SESSION",
            created_at=created_at,
            cutoff=cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[ref],
            payload={
                "objective": objective,
                "instrument": instrument,
                "research_role": role,
                "session_state": "OPEN",
                "objects_reviewed": [],
                "incidents": [],
                "unresolved_questions": [],
                "next_action": None,
            },
        )
        return self.writes.create_draft(draft, at=created_at, action="research.open-session")

    def add_observation(
        self,
        *,
        session_id: str,
        release_id: str,
        cutoff: str,
        visible_facts: dict[str, Any],
        unknowns: list[str],
        source_record_refs: list[str],
        created_at: str,
        model_refs: list[dict[str, Any]] | None = None,
        artifact_refs: list[dict[str, Any]] | None = None,
    ) -> str:
        draft = self.writes.base_record(
            record_type="OBSERVATION_SNAPSHOT",
            created_at=created_at,
            cutoff=cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[self.writes.release_ref(release_id, cutoff)],
            model_refs=model_refs,
            artifact_refs=artifact_refs,
            payload={
                "session_id": session_id,
                "visible_facts": deepcopy(visible_facts),
                "unknowns": list(unknowns),
                "source_record_refs": list(source_record_refs),
            },
            lineage={"parent": [session_id], "derived_from": list(source_record_refs), "supersedes": None, "adjudicates": []},
        )
        return self.writes.create_draft(draft, at=created_at, action="research.add-observation")

    def freeze_observation(self, *, draft_id: str, frozen_at: str) -> dict[str, Any]:
        return self.writes.freeze_draft(draft_id, frozen_at=frozen_at, action="research.freeze-observation")

    def freeze_claim(
        self,
        *,
        observation_id: str,
        release_id: str,
        cutoff: str,
        eligibility: Any,
        discriminator: Any,
        falsifier: Any,
        horizons: list[Any],
        frozen_at: str,
    ) -> dict[str, Any]:
        draft = self.writes.base_record(
            record_type="CLAIM_RECORD",
            created_at=frozen_at,
            cutoff=cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[self.writes.release_ref(release_id, cutoff)],
            payload={
                "observation_id": observation_id,
                "eligibility": eligibility,
                "discriminator": discriminator,
                "falsifier": falsifier,
                "horizons": horizons,
            },
            lineage={"parent": [observation_id], "derived_from": [observation_id], "supersedes": None, "adjudicates": []},
        )
        return self.writes.freeze_new(draft, frozen_at=frozen_at, action="research.freeze-claim")

    def register_realization(
        self,
        *,
        observation_id: str,
        release_id: str,
        cutoff: str,
        reference_time: str,
        horizon: str,
        coverage: Any,
        path: Any,
        censoring_state: str,
        frozen_at: str,
        claim_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "observation_id": observation_id,
            "reference_time": reference_time,
            "horizon": horizon,
            "coverage": coverage,
            "path": path,
            "censoring_state": censoring_state,
        }
        if claim_id:
            payload["claim_id"] = claim_id
        draft = self.writes.base_record(
            record_type="REALIZATION_SNAPSHOT",
            created_at=frozen_at,
            cutoff=cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[self.writes.release_ref(release_id, cutoff)],
            payload=payload,
            lineage={"parent": [observation_id], "derived_from": [observation_id], "supersedes": None, "adjudicates": []},
        )
        return self.writes.freeze_new(draft, frozen_at=frozen_at, action="research.register-realization")

    def adjudicate(
        self,
        *,
        observation_id: str,
        claim_id: str,
        realization_id: str,
        release_id: str,
        cutoff: str,
        evidence_role: str,
        admissibility: str,
        frozen_at: str,
    ) -> dict[str, Any]:
        draft = self.writes.base_record(
            record_type="EVIDENCE_ITEM",
            created_at=frozen_at,
            cutoff=cutoff,
            operator_id=self.writes.operator_id,
            source_release_refs=[self.writes.release_ref(release_id, cutoff)],
            payload={
                "observation_id": observation_id,
                "claim_id": claim_id,
                "realization_id": realization_id,
                "evidence_role": evidence_role,
                "admissibility": admissibility,
            },
            lineage={"parent": [claim_id, realization_id], "derived_from": [observation_id, claim_id, realization_id], "supersedes": None, "adjudicates": [claim_id]},
        )
        return self.writes.freeze_new(draft, frozen_at=frozen_at, action="research.adjudicate")

    def close_session(
        self,
        *,
        draft_id: str,
        incidents: list[str],
        unresolved_questions: list[str],
        next_action: str,
        frozen_at: str,
    ) -> dict[str, Any]:
        record = self.writes.drafts.read(draft_id)
        if record["record_type"] != "RESEARCH_SESSION":
            raise ValueError("close-session requires a RESEARCH_SESSION draft")
        record["payload"]["session_state"] = "CLOSED"
        record["payload"]["incidents"] = list(incidents)
        record["payload"]["unresolved_questions"] = list(unresolved_questions)
        record["payload"]["next_action"] = next_action
        self.writes.update_draft(draft_id, record, at=frozen_at, action="research.prepare-close-session")
        return self.writes.freeze_draft(draft_id, frozen_at=frozen_at, action="research.close-session")
