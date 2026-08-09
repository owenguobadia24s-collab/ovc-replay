import type { Investigation } from "../../api/types";
export const INVESTIGATION_QUERY_KEY = "investigation";
export const LOCAL_TAB_STORAGE_KEY = "ovc.rcn.fixture.investigation-tabs.v1";
export function selectActiveInvestigation(items: Investigation[], requested: string | null): Investigation | null { if (requested) { const exact = items.find((item) => item.investigation_id === requested); if (exact) return exact; } return items[0] ?? null; }
export function mergeLocalTabs(existing: string[], activeId: string): string[] { return [...new Set([activeId, ...existing.filter((id) => id !== activeId)].slice(0, 6))]; }
export function investigationSearch(activeId: string): URLSearchParams { const params = new URLSearchParams(); params.set(INVESTIGATION_QUERY_KEY, activeId); return params; }
