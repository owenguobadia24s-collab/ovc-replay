/** GENERATED CONTRACT SURFACE. Regenerate with `npm run types:generate`. */
export interface components {
  schemas: {
    FixtureBanner: { mode: "FIXTURE_ONLY"; data_classification: "SYNTHETIC_FIXTURE"; evidence_status: "NON_EVIDENTIARY"; authority_effect: "NONE" };
    SourceIdentity: { commit: string; release_id: string | null; contract_ids: string[]; schema_ids: string[]; logical_hashes: string[] };
    CapabilitySummary: { capability_id: string; available: boolean; authorised: boolean; active: boolean; authority_effect: "NONE" };
    Blocker: { reason_code: string; owner_programme?: string; decision_ref?: string; evidence_ref?: string };
    Dependency: { capability_id: string; relation: string; evidence_class: string };
    CapabilityDependencyStatus: { capability_id: string; display_name: string; implementation_state: string; source_materialization: string; source_compatibility: string; available: boolean; authorised: boolean; active: boolean; authority_effect: "NONE"; source_identity: components["schemas"]["SourceIdentity"]; blockers: components["schemas"]["Blocker"][]; dependencies: components["schemas"]["Dependency"][]; last_verified_commit: string };
    Investigation: { investigation_id: string; title: string; state: string; reason_code?: string; fixture: true };
  };
}
