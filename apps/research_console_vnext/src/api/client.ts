import type { CapabilityDependencyStatus, Investigation, ReadEnvelope, SourceIdentity } from "./types";

const API_ROOT = "/api/v1";

export class FixtureBoundaryError extends Error {
  readonly reasonCode: string;
  constructor(reasonCode: string) { super(reasonCode); this.name = "FixtureBoundaryError"; this.reasonCode = reasonCode; }
}

export function requireFixtureEnvelope<T>(value: ReadEnvelope<T>): ReadEnvelope<T> {
  const banner = value.fixture_banner;
  if (banner?.mode !== "FIXTURE_ONLY" || banner?.data_classification !== "SYNTHETIC_FIXTURE" || banner?.evidence_status !== "NON_EVIDENTIARY" || banner?.authority_effect !== "NONE") {
    throw new FixtureBoundaryError("FIXTURE_AUTHORITY_VIOLATION");
  }
  return value;
}

async function get<T>(path: string): Promise<ReadEnvelope<T>> {
  const response = await fetch(`${API_ROOT}${path}`, { method: "GET", headers: { Accept: "application/json" } });
  if (!response.ok) throw new FixtureBoundaryError(`HTTP_${response.status}`);
  return requireFixtureEnvelope((await response.json()) as ReadEnvelope<T>);
}

export async function getIdentity(): Promise<ReadEnvelope<SourceIdentity>> { return get<SourceIdentity>("/identity"); }
export async function getCapabilities(): Promise<ReadEnvelope<CapabilityDependencyStatus[]>> { return get<CapabilityDependencyStatus[]>("/capabilities"); }
export async function getInvestigations(): Promise<ReadEnvelope<{ items: Investigation[] }>> { return get<{ items: Investigation[] }>("/fixture/investigations"); }
