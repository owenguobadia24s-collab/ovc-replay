import ELK, { type ElkEdge, type ElkNode } from "./elk-runtime.js";
import type { AtlasVisualGraph } from "./model";

export type AtlasPosition = { x: number; y: number };
export type AtlasLayoutResult = {
  graphId: string;
  positions: Record<string, AtlasPosition>;
  width: number;
  height: number;
};

const layoutOptions = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.edgeRouting": "ORTHOGONAL",
  "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
  "elk.layered.cycleBreaking.strategy": "MODEL_ORDER",
  "elk.spacing.nodeNode": "38",
  "elk.layered.spacing.nodeNodeBetweenLayers": "80",
  "elk.padding": "[top=28,left=28,bottom=28,right=28]",
};

function toElkGraph(graph: AtlasVisualGraph): ElkNode {
  const childMap = new Map<string | undefined, ElkNode[]>();
  for (const node of [...graph.nodes].sort((left, right) => left.id.localeCompare(right.id))) {
    const children = childMap.get(node.parent) ?? [];
    children.push({ id: node.id, width: 136, height: 52 });
    childMap.set(node.parent, children);
  }
  for (const [parentId, children] of childMap) {
    if (!parentId) continue;
    const parent = [...childMap.values()].flat().find((node) => node.id === parentId);
    if (parent) parent.children = children;
  }
  const edges: ElkEdge[] = [...graph.edges]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((edge) => ({ id: edge.id, sources: [edge.source], targets: [edge.target] }));
  return {
    id: graph.graphId,
    layoutOptions,
    children: childMap.get(undefined) ?? [],
    edges,
  };
}

function collectPositions(node: ElkNode, parentX: number, parentY: number, positions: Record<string, AtlasPosition>): void {
  const x = parentX + (node.x ?? 0);
  const y = parentY + (node.y ?? 0);
  if (node.id && !node.id.startsWith("synthetic:visual:")) positions[node.id] = { x, y };
  for (const child of node.children ?? []) collectPositions(child, x, y, positions);
}

export async function layoutAtlasGraph(graph: AtlasVisualGraph): Promise<AtlasLayoutResult> {
  const laidOut = await new ELK().layout(toElkGraph(graph));
  const positions: Record<string, AtlasPosition> = {};
  collectPositions(laidOut, 0, 0, positions);
  if (Object.keys(positions).length !== graph.nodes.length) throw new Error("ELK_LAYOUT_INCOMPLETE");
  return {
    graphId: graph.graphId,
    positions,
    width: Math.ceil(laidOut.width ?? 0),
    height: Math.ceil(laidOut.height ?? 0),
  };
}
