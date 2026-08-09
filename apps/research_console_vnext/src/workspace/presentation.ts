import type { CapabilitySummary, EvidenceItem } from "../api/types";

export type DensityMode = "comfortable" | "compact" | "dense";
export const DENSITY_MODES: DensityMode[] = ["comfortable", "compact", "dense"];
export function densityLabel(value: DensityMode): string { return value[0].toUpperCase() + value.slice(1); }
export function capabilityReason(capability?: CapabilitySummary): string {
  if (!capability) return "Fixture capability pending";
  if (!capability.available) return "Capability unavailable in fixture source";
  if (!capability.authorised) return "Capability available but not authorised";
  if (!capability.active) return "Capability authorised but inactive";
  return "Capability available, authorised and active";
}
export function evidenceByKind(items: EvidenceItem[], kind: string): EvidenceItem[] { return items.filter((item) => item.kind === kind); }
export function nonEmpty(value: string | undefined | null, fallback: string): string { return value && value.trim() ? value : fallback; }
