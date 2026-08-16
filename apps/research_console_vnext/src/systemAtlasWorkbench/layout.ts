import type { AtlasNode } from "./model";

export type AtlasPosition = { x: number; y: number };

export function stableAtlasPosition(node: AtlasNode): AtlasPosition {
  if (node.family === "domain") return { x: 62, y: 140 + node.lane * 245 };
  if (node.lane === 3) return { x: 380 + node.order * 175, y: 855 };
  return { x: 160 + node.order * 155, y: 140 + node.lane * 245 };
}

export function maxLayoutDisplacement(before: AtlasNode[], after: AtlasNode[]): number {
  const previous = new Map(before.map((node) => [node.id, stableAtlasPosition(node)]));
  return after.reduce((maximum, node) => {
    const oldPosition = previous.get(node.id);
    if (!oldPosition) return maximum;
    const nextPosition = stableAtlasPosition(node);
    return Math.max(maximum, Math.hypot(nextPosition.x - oldPosition.x, nextPosition.y - oldPosition.y));
  }, 0);
}
