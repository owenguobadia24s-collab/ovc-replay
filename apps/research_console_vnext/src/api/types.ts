import type { components } from "./generated/schema";

export type FixtureBanner = components["schemas"]["FixtureBanner"];
export type SourceIdentity = components["schemas"]["SourceIdentity"];
export type CapabilityDependencyStatus = components["schemas"]["CapabilityDependencyStatus"];
export type Investigation = components["schemas"]["Investigation"];

export type CapabilitySummary = { capability_id: string; available: boolean; authorised: boolean; active: boolean; authority_effect: "NONE" };
export type ReadEnvelope<T> = { fixture_banner: FixtureBanner; schema_id: string; resource: string; source_identity: SourceIdentity; capability: CapabilitySummary; payload: T };

export type MarketBar = { t: string; o: number; h: number; l: number; c: number };
export type MarketWindow = { items: MarketBar[]; total: number; truncated: boolean };
export type C2StateView = { availability: string; axes: Record<string, string>; computability: Record<string, string>; first_valid_time?: string };
export type C2EView = { availability: string; reason_code?: string; episodes: unknown[]; events: unknown[] };
export type OccurrenceContextView = { instrument?: string; clock?: string; side?: string; session?: string; occurrence_id: string; context_id?: string; source?: string; availability?: string; reason_code?: string };
export type EvidenceItem = { evidence_id: string; kind: string; record_ref: string };
export type EvidencePage = { items: EvidenceItem[]; next_cursor: number | null; total: number };
export type FamilyEvidenceView = { family_id: string | null; assignment_status: string; reason_code?: string; authority_effect?: "NONE" };
