import type {
  CapabilityDependencyStatus,
  C2EView,
  C2StateView,
  EvidencePage,
  FamilyEvidenceView,
  Investigation,
  MarketWindow,
  OccurrenceContextView,
  ReadEnvelope,
  SourceIdentity,
  WP5ARepresentationSnapshot,
  WP5B1DMRPSnapshot,
} from "./types";

const API_ROOT = "/api/v1";
const DMRP_SNAPSHOT_PATH = "/research/dmrp/snapshot";

export class FixtureBoundaryError extends Error {
  readonly reasonCode: string;
  constructor(reasonCode: string) {
    super(reasonCode);
    this.name = "FixtureBoundaryError";
    this.reasonCode = reasonCode;
  }
}

export function requireFixtureEnvelope<T>(value: ReadEnvelope<T>): ReadEnvelope<T> {
  const banner = value.fixture_banner;
  if (
    banner?.mode !== "FIXTURE_ONLY" ||
    banner?.data_classification !== "SYNTHETIC_FIXTURE" ||
    banner?.evidence_status !== "NON_EVIDENTIARY" ||
    banner?.authority_effect !== "NONE"
  ) {
    throw new FixtureBoundaryError("FIXTURE_AUTHORITY_VIOLATION");
  }
  return value;
}

async function get<T>(path: string): Promise<ReadEnvelope<T>> {
  const response = await fetch(`${API_ROOT}${path}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new FixtureBoundaryError(`HTTP_${response.status}`);
  }
  return requireFixtureEnvelope((await response.json()) as ReadEnvelope<T>);
}

export async function getIdentity(): Promise<ReadEnvelope<SourceIdentity>> {
  return get<SourceIdentity>("/identity");
}
export async function getCapabilities(): Promise<ReadEnvelope<CapabilityDependencyStatus[]>> {
  return get<CapabilityDependencyStatus[]>("/capabilities");
}
export async function getInvestigations(): Promise<ReadEnvelope<{ items: Investigation[] }>> {
  return get<{ items: Investigation[] }>("/fixture/investigations");
}
export async function getMarketWindow(): Promise<ReadEnvelope<MarketWindow>> {
  return get<MarketWindow>("/market/window?limit=500");
}
export async function getC2State(): Promise<ReadEnvelope<C2StateView>> {
  return get<C2StateView>("/c2/state");
}
export async function getC2E(): Promise<ReadEnvelope<C2EView>> {
  return get<C2EView>("/c2e/episodes");
}
export async function getOccurrenceContext(): Promise<ReadEnvelope<OccurrenceContextView>> {
  return get<OccurrenceContextView>("/occurrences/occ%3Asynthetic%3A001/context");
}
export async function getEvidence(): Promise<ReadEnvelope<EvidencePage>> {
  return get<EvidencePage>("/evidence/objects?limit=50");
}
export async function getFamilies(): Promise<ReadEnvelope<FamilyEvidenceView[]>> {
  return get<FamilyEvidenceView[]>("/research/families");
}
export async function getRepresentationSnapshot(): Promise<ReadEnvelope<WP5ARepresentationSnapshot>> {
  return get<WP5ARepresentationSnapshot>("/research/representations/snapshot");
}

export async function getDMRPSnapshot(): Promise<any> {
  const response = await fetch(`${API_ROOT}${DMRP_SNAPSHOT_PATH}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new FixtureBoundaryError(`HTTP_${response.status}`);
  }
  const value = await response.json();
  if (value?.fixture_banner) {
    return requireFixtureEnvelope(value as ReadEnvelope<WP5B1DMRPSnapshot>);
  }
  const banner = value?.real_source_banner;
  if (
    banner?.mode !== "REAL_SOURCE_READ_ONLY" ||
    banner?.data_classification !== "DMRP_OWNER_COURT_RECORD" ||
    banner?.presentation_authority !== "RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]" ||
    banner?.source_owner_authority !== "UNCHANGED" ||
    banner?.authority_effect !== "NONE" ||
    banner?.fixture_fallback !== "PROHIBITED" ||
    banner?.source_admission_transitivity !== "PROHIBITED"
  ) {
    throw new FixtureBoundaryError("DMRP_REAL_SOURCE_AUTHORITY_VIOLATION");
  }
  return value;
}
