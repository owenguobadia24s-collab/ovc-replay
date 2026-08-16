// Generated from src/ovc/system_atlas/generated/atlas_openapi_v0_1.json. Do not edit manually.
export type AtlasVisibility = "ATLAS_PUBLIC_METADATA" | "ATLAS_INTERNAL" | "ATLAS_RESTRICTED";
export type AtlasQueryFamily = "SEARCH" | "TRACE" | "DEPENDENCY" | "IMPACT" | "EXPLAIN" | "AUTHORITY" | "OWNERSHIP" | "WHY_BLOCKED" | "HISTORY" | "DIFF";
export interface AtlasEnvelope<T> { schema: "ovc-atlas-api-envelope/v1"; graph_generation: string; repository_tree: string; query_policy_version: string; completeness_profile: string; security_visibility: AtlasVisibility[]; warnings: string[]; write_effect: "NONE"; data: T; }
export interface AtlasQueryRequest { family: AtlasQueryFamily; term?: string; start_id?: string; entity_id?: string; object_id?: string; changed_entity_ids?: string[]; max_depth?: number; direction?: "OUTBOUND" | "INBOUND" | "BOTH"; predicates?: string[]; relationship_families?: string[]; }
export interface AtlasViewRequest { entity_ids?: string[]; maximum_entities?: number; }
export class AtlasClient {
  constructor(private readonly baseUrl: string, private readonly fetcher: typeof fetch = fetch) {}
  private async call<T>(path: string, init?: RequestInit): Promise<AtlasEnvelope<T>> { const response = await this.fetcher(`${this.baseUrl}${path}`, init); const body = await response.json() as AtlasEnvelope<T>; if (!response.ok) throw Object.assign(new Error(`Atlas API ${response.status}`), { response: body }); return body; }
  meta<T = unknown>(): Promise<AtlasEnvelope<T>> { return this.call<T>("/api/v1/atlas/meta"); }
  query<T = unknown>(request: AtlasQueryRequest): Promise<AtlasEnvelope<T>> { return this.call<T>("/api/v1/atlas/query", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(request) }); }
  view<T = unknown>(request: AtlasViewRequest): Promise<AtlasEnvelope<T>> { return this.call<T>("/api/v1/atlas/view", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(request) }); }
}
