import { atlasProjection, type AtlasQueryFamily, type AtlasSurfaceId } from "./model";

export const inspectorTabs = ["Overview", "Relations", "Implementation", "Authority", "Evidence", "History"] as const;
export type InspectorTab = (typeof inspectorTabs)[number];
export type AtlasViewMode = "graph" | "table";

export type AtlasWorkbenchState = {
  surfaceId: AtlasSurfaceId;
  queryFamily: AtlasQueryFamily;
  viewMode: AtlasViewMode;
  selectedId: string;
  traceId: string;
  tab: InspectorTab;
  search: string;
  authorityVisible: boolean;
};

const surfaceIds = new Set(atlasProjection.surface_definitions.map((surface) => surface.id));
const queryFamilies = new Set(atlasProjection.query_definitions.map((query) => query.id));
const traceIds = new Set(["whole-system", ...atlasProjection.traces.map((trace) => trace.id)]);
const nodeIds = new Set(atlasProjection.nodes.map((node) => node.id));

export function defaultWorkbenchState(surfaceId: AtlasSurfaceId = "architecture"): AtlasWorkbenchState {
  const surface = atlasProjection.surface_definitions.find((item) => item.id === surfaceId) ?? atlasProjection.surface_definitions[0];
  const defaultNode = surface.id === "research" ? "question"
    : surface.id === "execution" ? "continue"
      : surface.id === "authority" ? "c25"
        : surface.id === "history" ? "opt-c"
          : "c2e";
  return {
    surfaceId: surface.id,
    queryFamily: surface.default_query,
    viewMode: "graph",
    selectedId: defaultNode,
    traceId: surface.default_trace,
    tab: "Overview",
    search: "",
    authorityVisible: true,
  };
}

export function parseWorkbenchState(search: string): AtlasWorkbenchState {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const surfaceValue = params.get("surface") as AtlasSurfaceId;
  const state = defaultWorkbenchState(surfaceIds.has(surfaceValue) ? surfaceValue : "architecture");
  const query = params.get("query") as AtlasQueryFamily;
  const view = params.get("view") as AtlasViewMode;
  const node = params.get("node") ?? "";
  const trace = params.get("trace") ?? "";
  const tab = params.get("tab") as InspectorTab;
  return {
    ...state,
    queryFamily: queryFamilies.has(query) ? query : state.queryFamily,
    viewMode: view === "table" ? "table" : "graph",
    selectedId: nodeIds.has(node) ? node : state.selectedId,
    traceId: traceIds.has(trace) ? trace : state.traceId,
    tab: inspectorTabs.includes(tab) ? tab : state.tab,
    search: (params.get("q") ?? "").slice(0, 200),
    authorityVisible: params.get("authority") !== "0",
  };
}

export function serializeWorkbenchState(state: AtlasWorkbenchState): string {
  const params = new URLSearchParams();
  params.set("surface", state.surfaceId);
  params.set("query", state.queryFamily);
  params.set("view", state.viewMode);
  params.set("node", state.selectedId);
  params.set("trace", state.traceId);
  params.set("tab", state.tab);
  if (state.search) params.set("q", state.search);
  params.set("authority", state.authorityVisible ? "1" : "0");
  return `?${params.toString()}`;
}
