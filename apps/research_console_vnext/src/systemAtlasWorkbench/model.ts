import fixture from "../../../../fixtures/system_atlas/wp9/ATLAS_WORKBENCH_ACTUAL_REPOSITORY_PROJECTION_v0_1.json";
import liveBinding from "../../../../fixtures/system_atlas/wp10/ATLAS_WP10_LIVE_CURRENT_SHADOW_BINDING_v0_1.json";

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
export type AtlasSurfaceId = "architecture" | "research" | "execution" | "authority" | "repository" | "history";
export type AtlasQueryFamily = "SEARCH" | "TRACE" | "DEPENDENCY" | "IMPACT" | "EXPLAIN" | "AUTHORITY" | "OWNERSHIP" | "WHY_BLOCKED" | "HISTORY" | "DIFF";
export type AtlasSurface = { id: AtlasSurfaceId; label: string; default_query: AtlasQueryFamily; default_trace: string; node_ids: string[] };
export type AtlasQueryDefinition = { id: AtlasQueryFamily; label: string; representations: ["GRAPH", "TABLE"]; equivalence_receipt: string };
export type AtlasProjection = {
  schema: string;
  projection_id: string;
  source_commit: string;
  source_tree: string;
  reality_class: "CURRENT";
  qualification_class: "ACTUAL_REPOSITORY_SHADOW_NOT_CONSOLE_SOURCE";
  authority_effect: "NONE_PRESENTATION_ONLY";
  current_pointer_published: false;
  research_console_binding_created: false;
  surface_definitions: AtlasSurface[];
  query_definitions: AtlasQueryDefinition[];
  inspector_tabs: string[];
  deep_link_contract: { fields: string[]; typed_context_only: true; source_mutation_effect: "NONE" };
  presentation_state: { features: string[]; storage: "BROWSER_LOCAL_ONLY"; authority_effect: "NONE" };
  nodes: AtlasNode[];
  edges: AtlasEdge[];
  traces: AtlasTrace[];
};

const sourceByNode = new Map(liveBinding.source_bindings.map((source) => [source.node_id, source]));
if (sourceByNode.size !== fixture.nodes.length || fixture.nodes.some((node) => !sourceByNode.has(node.id))) {
  throw new Error("ATLAS_LIVE_SHADOW_SOURCE_BINDINGS_INCOMPLETE");
}

export const atlasProjection = {
  ...fixture,
  projection_id: "ATLAS-WP10-LIVE-CURRENT-SHADOW-v0.1",
  source_commit: liveBinding.source_commit,
  source_tree: liveBinding.source_tree,
  nodes: fixture.nodes.map((node) => {
    const source = sourceByNode.get(node.id)!;
    return { ...node, source: { path: source.path, blob: source.blob } };
  }),
} as unknown as AtlasProjection;

export type AtlasQueryProjection = {
  nodeIds: Set<string>;
  edgeIds: Set<string>;
  warning?: string;
};

export function nodesForTrace(traceId: string): Set<string> | undefined {
  if (traceId === "whole-system") return undefined;
  const trace = atlasProjection.traces.find((item) => item.id === traceId);
  return trace ? new Set(trace.node_ids) : undefined;
}

export function relatedEdges(nodeId: string): AtlasEdge[] {
  return atlasProjection.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId);
}

function surfaceNodeIds(surfaceId: AtlasSurfaceId): Set<string> {
  const surface = atlasProjection.surface_definitions.find((item) => item.id === surfaceId);
  return new Set(surface?.node_ids.length ? surface.node_ids : atlasProjection.nodes.map((node) => node.id));
}

function reachableFrom(seed: string, allowed: Set<string>): Set<string> {
  const reached = new Set<string>(allowed.has(seed) ? [seed] : []);
  let frontier = [...reached];
  for (let depth = 0; depth < 3 && frontier.length; depth += 1) {
    const next: string[] = [];
    for (const source of frontier) {
      for (const edge of atlasProjection.edges) {
        if (edge.source !== source || !allowed.has(edge.target) || reached.has(edge.target)) continue;
        reached.add(edge.target);
        next.push(edge.target);
      }
    }
    frontier = next;
  }
  return reached;
}

export function projectWorkbenchQuery(input: {
  surfaceId: AtlasSurfaceId;
  family: AtlasQueryFamily;
  selectedId: string;
  traceId: string;
  search: string;
}): AtlasQueryProjection {
  const allowed = surfaceNodeIds(input.surfaceId);
  const selected = allowed.has(input.selectedId) ? input.selectedId : [...allowed][0] ?? "";
  let nodeIds = new Set(allowed);
  let warning: string | undefined;

  if (input.family === "SEARCH") {
    const needle = input.search.trim().toLowerCase();
    if (needle) nodeIds = new Set(atlasProjection.nodes.filter((node) => allowed.has(node.id) && `${node.id} ${node.label} ${node.source.path}`.toLowerCase().includes(needle)).map((node) => node.id));
  } else if (input.family === "TRACE") {
    const traced = nodesForTrace(input.traceId);
    if (traced) nodeIds = new Set([...traced].filter((id) => allowed.has(id)));
  } else if (input.family === "DEPENDENCY") {
    nodeIds = new Set(selected ? [selected] : []);
    relatedEdges(selected).forEach((edge) => {
      if (["dependency", "structural", "implementation", "assurance"].includes(edge.family)) {
        if (allowed.has(edge.source)) nodeIds.add(edge.source);
        if (allowed.has(edge.target)) nodeIds.add(edge.target);
      }
    });
  } else if (input.family === "IMPACT") {
    nodeIds = reachableFrom(selected, allowed);
  } else if (input.family === "EXPLAIN") {
    nodeIds = new Set(selected ? [selected] : []);
  } else if (input.family === "AUTHORITY") {
    nodeIds = new Set(atlasProjection.nodes.filter((node) => allowed.has(node.id) && (node.family === "authority" || node.state === "reserved" || node.state === "forbidden")).map((node) => node.id));
  } else if (input.family === "OWNERSHIP") {
    const ownershipEdges = atlasProjection.edges.filter((edge) => edge.family === "ownership" && allowed.has(edge.source) && allowed.has(edge.target));
    nodeIds = new Set(ownershipEdges.flatMap((edge) => [edge.source, edge.target]));
    if (!nodeIds.size) warning = "No canonical ownership relation is present in this bounded projection.";
  } else if (input.family === "WHY_BLOCKED") {
    nodeIds = new Set(atlasProjection.nodes.filter((node) => allowed.has(node.id) && (node.state === "reserved" || node.state === "forbidden")).map((node) => node.id));
  } else if (input.family === "HISTORY") {
    nodeIds = new Set(atlasProjection.nodes.filter((node) => allowed.has(node.id) && node.state === "historical").map((node) => node.id));
  } else if (input.family === "DIFF") {
    nodeIds = new Set();
    warning = "A comparison generation is required for DIFF; none is bound to this current-only projection.";
  }

  const edgeIds = new Set(atlasProjection.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)).map((edge) => edge.id));
  return { nodeIds, edgeIds, warning };
}
