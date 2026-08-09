import type { components } from "./generated/schema";

export type FixtureBanner = components["schemas"]["FixtureBanner"];
export type SourceIdentity = components["schemas"]["SourceIdentity"];
export type CapabilityDependencyStatus = components["schemas"]["CapabilityDependencyStatus"];
export type Investigation = components["schemas"]["Investigation"];

export type CapabilitySummary = { capability_id: string; available: boolean; authorised: boolean; active: boolean; authority_effect: "NONE" };
export type ReadEnvelope<T> = { fixture_banner: FixtureBanner; schema_id: string; resource: string; source_identity: SourceIdentity; capability: CapabilitySummary; payload: T };
