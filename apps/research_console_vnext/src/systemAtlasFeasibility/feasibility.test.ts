import cytoscape from "cytoscape";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AtlasFeasibilityCanvas, toCytoscapeElements } from "./AtlasFeasibilityCanvas";
import { layoutAtlasGraph } from "./layout";
import { buildCompoundC2EGraph, buildL1SyntheticGraph, buildStressGraph } from "./model";
import { atlasStyles } from "./styles";

describe("ATLAS-WP1V visual dependency feasibility", () => {
  it("reproduces the exact deterministic L1 layout", async () => {
    const graph = buildL1SyntheticGraph();
    const first = await layoutAtlasGraph(graph);
    const second = await layoutAtlasGraph({ ...graph, nodes: [...graph.nodes].reverse(), edges: [...graph.edges].reverse() });
    expect(second).toEqual(first);
    expect(Object.values(first.positions).every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y))).toBe(true);
  });

  it("renders the compound C2E graph through Cytoscape preset positions", async () => {
    const graph = buildCompoundC2EGraph();
    const layout = await layoutAtlasGraph(graph);
    const instance = cytoscape({ headless: true, elements: toCytoscapeElements(graph, layout), style: atlasStyles, layout: { name: "preset" } });
    expect(instance.nodes().length).toBe(graph.nodes.length);
    expect(instance.edges().length).toBe(graph.edges.length);
    expect(instance.nodes("[state = 'conflict']").length).toBeGreaterThan(0);
    expect(instance.nodes(":parent").length).toBe(5);
    instance.destroy();
  });

  it("materializes authority and prohibition edge classes in the L1 graph", async () => {
    const graph = buildL1SyntheticGraph();
    const layout = await layoutAtlasGraph(graph);
    const instance = cytoscape({ headless: true, elements: toCytoscapeElements(graph, layout), style: atlasStyles, layout: { name: "preset" } });
    expect(instance.edges("[family = 'authority']").length).toBe(2);
    expect(instance.edges("[family = 'prohibition'][state = 'forbidden']").length).toBe(1);
    instance.destroy();
  });

  it("keeps deterministic relayout within the declared canvas displacement budget", async () => {
    const base = buildL1SyntheticGraph();
    const expanded = {
      ...base,
      graphId: `${base.graphId}:expanded`,
      nodes: [...base.nodes, { id: "l1:assurance", label: "Assurance", family: "record" as const, state: "current" as const }],
      edges: [...base.edges, { id: "l1:atlas-assurance", source: "l1:atlas", target: "l1:assurance", family: "structural" as const, state: "current" as const }],
    };
    const [before, after, repeated] = await Promise.all([
      layoutAtlasGraph(base),
      layoutAtlasGraph(expanded),
      layoutAtlasGraph({ ...expanded, nodes: [...expanded.nodes].reverse(), edges: [...expanded.edges].reverse() }),
    ]);
    const displacements = base.nodes.map(({ id }) => Math.hypot(
      after.positions[id].x - before.positions[id].x,
      after.positions[id].y - before.positions[id].y,
    ));
    const displacementBudget = Math.max(after.width, after.height);
    expect(Math.max(...displacements)).toBeLessThanOrEqual(displacementBudget);
    expect(repeated).toEqual(after);
  });

  it("keeps the React harness synthetic and unbound to Console sources", async () => {
    const graph = buildL1SyntheticGraph();
    const layout = await layoutAtlasGraph(graph);
    const markup = renderToStaticMarkup(createElement(AtlasFeasibilityCanvas, { graph, layout, label: "Synthetic Atlas" }));
    expect(markup).toContain("atlas-feasibility-canvas");
    expect(graph.courtRecordStatus).toBe("SYNTHETIC_NOT_COURT_RECORD");
    expect(graph.authorityEffect).toBe("NONE_PRESENTATION_ONLY");
  });

  it("lays out the Windows stress profile without missing or non-finite positions", async () => {
    const graph = buildStressGraph(600, 12);
    const started = performance.now();
    const layout = await layoutAtlasGraph(graph);
    const elapsedMs = performance.now() - started;
    expect(Object.keys(layout.positions)).toHaveLength(600);
    expect(Object.values(layout.positions).every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y))).toBe(true);
    expect(elapsedMs).toBeLessThan(30_000);
  }, 35_000);

  it("uses redundant grayscale-safe styling for reserved conflict historical and forbidden states", () => {
    const serialized = JSON.stringify(atlasStyles);
    expect(serialized).toContain("border-style");
    expect(serialized).toContain("line-style");
    expect(serialized).toContain("opacity");
    expect(serialized).toContain("target-arrow-shape");
    expect(serialized).toContain("prohibition");
  });
});
