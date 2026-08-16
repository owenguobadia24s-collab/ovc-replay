export type AtlasVisualState = "current" | "historical" | "forbidden" | "conflict" | "reserved";
export type AtlasVisualFamily = "domain" | "programme" | "service" | "record" | "implementation";
export type AtlasVisualEdgeFamily = "structural" | "data" | "dependency" | "authority" | "prohibition";

export type AtlasVisualNode = {
  id: string;
  label: string;
  family: AtlasVisualFamily;
  state: AtlasVisualState;
  parent?: string;
};

export type AtlasVisualEdge = {
  id: string;
  source: string;
  target: string;
  family: AtlasVisualEdgeFamily;
  state: AtlasVisualState;
};

export type AtlasVisualGraph = {
  graphId: string;
  nodes: AtlasVisualNode[];
  edges: AtlasVisualEdge[];
  courtRecordStatus: "SYNTHETIC_NOT_COURT_RECORD";
  authorityEffect: "NONE_PRESENTATION_ONLY";
};

const domainRows: Array<[string, string, AtlasVisualFamily]> = [
  ["market", "Market", "domain"],
  ["research", "Research", "domain"],
  ["governance", "Governance", "domain"],
  ["development", "Development", "domain"],
  ["shared", "Shared Systems", "service"],
  ["console", "Research Console", "service"],
  ["storage", "Storage / External", "service"],
  ["atlas", "System Atlas", "programme"],
];

export function buildL1SyntheticGraph(): AtlasVisualGraph {
  const nodes = domainRows.map(([id, label, family]) => ({
    id: `l1:${id}`,
    label,
    family,
    state: id === "atlas" ? "reserved" as const : "current" as const,
  }));
  const edges: AtlasVisualEdge[] = [
    ["market-research", "market", "research", "data", "current"],
    ["research-governance", "research", "governance", "dependency", "current"],
    ["governance-development", "governance", "development", "authority", "current"],
    ["development-shared", "development", "shared", "dependency", "current"],
    ["shared-console", "shared", "console", "data", "current"],
    ["console-storage", "console", "storage", "data", "current"],
    ["atlas-console", "atlas", "console", "prohibition", "forbidden"],
    ["governance-atlas", "governance", "atlas", "authority", "reserved"],
  ].map(([id, source, target, family, state]) => ({
    id: `l1:${id}`,
    source: `l1:${source}`,
    target: `l1:${target}`,
    family: family as AtlasVisualEdgeFamily,
    state: state as AtlasVisualState,
  }));
  return {
    graphId: "synthetic:visual:l1-whole-system.v0.1",
    nodes,
    edges,
    courtRecordStatus: "SYNTHETIC_NOT_COURT_RECORD",
    authorityEffect: "NONE_PRESENTATION_ONLY",
  };
}

export function buildCompoundC2EGraph(): AtlasVisualGraph {
  const groups = ["contracts", "records", "implementation", "assurance"];
  const nodes: AtlasVisualNode[] = [
    { id: "c2e", label: "C2E", family: "programme", state: "current" },
    ...groups.map((group) => ({ id: `c2e:${group}`, label: group.toUpperCase(), family: "implementation" as const, state: "current" as const, parent: "c2e" })),
  ];
  for (const group of groups) {
    for (let index = 0; index < 6; index += 1) {
      nodes.push({
        id: `c2e:${group}:${String(index).padStart(2, "0")}`,
        label: `${group.slice(0, 3).toUpperCase()} ${index + 1}`,
        family: group === "records" ? "record" : "implementation",
        state: index === 4 ? "historical" : index === 5 ? "conflict" : "current",
        parent: `c2e:${group}`,
      });
    }
  }
  const edges: AtlasVisualEdge[] = [];
  for (let index = 0; index < 6; index += 1) {
    edges.push({
      id: `c2e:contract-record:${index}`,
      source: `c2e:contracts:${String(index).padStart(2, "0")}`,
      target: `c2e:records:${String(index).padStart(2, "0")}`,
      family: "structural",
      state: "current",
    });
    edges.push({
      id: `c2e:record-implementation:${index}`,
      source: `c2e:records:${String(index).padStart(2, "0")}`,
      target: `c2e:implementation:${String(index).padStart(2, "0")}`,
      family: "dependency",
      state: index === 5 ? "conflict" : "current",
    });
    edges.push({
      id: `c2e:implementation-assurance:${index}`,
      source: `c2e:implementation:${String(index).padStart(2, "0")}`,
      target: `c2e:assurance:${String(index).padStart(2, "0")}`,
      family: "data",
      state: index === 4 ? "historical" : "current",
    });
  }
  return {
    graphId: "synthetic:visual:c2e-compound.v0.1",
    nodes,
    edges,
    courtRecordStatus: "SYNTHETIC_NOT_COURT_RECORD",
    authorityEffect: "NONE_PRESENTATION_ONLY",
  };
}

export function buildStressGraph(nodeCount = 600, groupCount = 12): AtlasVisualGraph {
  if (nodeCount < groupCount || groupCount < 1) throw new Error("invalid stress graph dimensions");
  const nodes: AtlasVisualNode[] = [];
  const edges: AtlasVisualEdge[] = [];
  for (let index = 0; index < nodeCount; index += 1) {
    nodes.push({
      id: `stress:${String(index).padStart(4, "0")}`,
      label: `N${index}`,
      family: index % 5 === 0 ? "programme" : "implementation",
      state: index % 47 === 0 ? "conflict" : index % 31 === 0 ? "historical" : "current",
    });
    if (index > 0) {
      edges.push({
        id: `stress:chain:${String(index).padStart(4, "0")}`,
        source: `stress:${String(index - 1).padStart(4, "0")}`,
        target: `stress:${String(index).padStart(4, "0")}`,
        family: index % 7 === 0 ? "authority" : "dependency",
        state: index % 53 === 0 ? "forbidden" : "current",
      });
    }
    if (index >= groupCount) {
      edges.push({
        id: `stress:cross:${String(index).padStart(4, "0")}`,
        source: `stress:${String(index - groupCount).padStart(4, "0")}`,
        target: `stress:${String(index).padStart(4, "0")}`,
        family: "data",
        state: "current",
      });
    }
  }
  return {
    graphId: `synthetic:visual:stress-${nodeCount}-${groupCount}.v0.1`,
    nodes,
    edges,
    courtRecordStatus: "SYNTHETIC_NOT_COURT_RECORD",
    authorityEffect: "NONE_PRESENTATION_ONLY",
  };
}
