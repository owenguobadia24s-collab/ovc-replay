// Generated-client compatibility smoke shape. NON_EVIDENTIARY fixture only.
export type FixtureBanner = { mode: 'FIXTURE_ONLY'; data_classification: 'SYNTHETIC_FIXTURE'; evidence_status: 'NON_EVIDENTIARY'; authority_effect: 'NONE' };
export type ReadEnvelope<T> = { fixture_banner: FixtureBanner; resource: string; payload: T };
