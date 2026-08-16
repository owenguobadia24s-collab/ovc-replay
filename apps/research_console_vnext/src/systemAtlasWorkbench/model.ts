import fixture from "../../../../fixtures/system_atlas/wp8/ATLAS_VS0_ACTUAL_REPOSITORY_PROJECTION_v0_1.json";

export type AtlasState = "current" | "historical" | "forbidden" | "reserved";
export type AtlasNode = {
  id: string;
  label: string;
  domain: string;
  family: string;
  state: AtlasState;
  reality: string;
  depth: number;
  lane: number;
  order: number;
  parent?: string;
  source: { path: string; blob: string };
};
export type AtlasEdge = { id: string; source: string; target: string; family: string; state: AtlasState };
export type AtlasTrace = { id: string; label: string; node_ids: string[] };
export type AtlasProjection = {
  schema: string;
  projection_id: string;
  source_commit: string;
  source_tree: string;
  qualification_class: "ACTUAL_REPOSITORY_SHADOW_NOT_CONSOLE_SOURCE";
  authority_effect: "NONE_PRESENTATION_ONLY";
  current_pointer_published: false;
  research_console_binding_created: false;
  nodes: AtlasNode[];
  edges: AtlasEdge[];
  traces: AtlasTrace[];
};

export const atlasProjection = fixture as AtlasProjection;

export function nodesForTrace(traceId: string): Set<string> | undefined {
  if (traceId === "whole-system") return undefined;
  const trace = atlasProjection.traces.find((item) => item.id === traceId);
  return trace ? new Set(trace.node_ids) : undefined;
}

export function relatedEdges(nodeId: string): AtlasEdge[] {
  return atlasProjection.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId);
}
