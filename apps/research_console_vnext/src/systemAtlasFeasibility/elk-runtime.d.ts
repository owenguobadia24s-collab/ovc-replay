export type ElkEdge = { id: string; sources: string[]; targets: string[] };
export type ElkNode = {
  id: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  children?: ElkNode[];
  edges?: ElkEdge[];
  layoutOptions?: Record<string, string>;
};

export default class ELK {
  layout(graph: ElkNode): Promise<ElkNode>;
}
