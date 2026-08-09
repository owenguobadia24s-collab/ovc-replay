// Generated-client compatibility smoke shape. SYNTHETIC_FIXTURE / NON_EVIDENTIARY only.
export type FixtureBanner = { mode: 'FIXTURE_ONLY'; data_classification: 'SYNTHETIC_FIXTURE'; evidence_status: 'NON_EVIDENTIARY'; authority_effect: 'NONE' };
export type SourceIdentity = { commit: string; release_id: string | null; contract_ids: string[]; schema_ids: string[]; logical_hashes: string[] };
export type CapabilitySummary = { capability_id: string; available: boolean; authorised: boolean; active: boolean; authority_effect: 'NONE' };
export type ReadEnvelope<T> = { fixture_banner: FixtureBanner; schema_id: string; resource: string; source_identity: SourceIdentity; capability: CapabilitySummary; payload: T };
