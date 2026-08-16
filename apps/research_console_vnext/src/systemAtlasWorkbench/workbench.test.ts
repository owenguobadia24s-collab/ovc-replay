import { describe, expect, it } from "vitest";
import { maxLayoutDisplacement, stableAtlasPosition } from "./layout";
import { atlasProjection, nodesForTrace, projectWorkbenchQuery } from "./model";
import { defaultWorkbenchState, parseWorkbenchState, serializeWorkbenchState } from "./workbenchState";

describe("System Atlas actual repository workbench", () => {
  it("keeps stable geography deterministic", () => {
    const first = atlasProjection.nodes.map(stableAtlasPosition);
    const second = atlasProjection.nodes.map(stableAtlasPosition);
    expect(first).toEqual(second);
    expect(maxLayoutDisplacement(atlasProjection.nodes, [...atlasProjection.nodes].reverse())).toBe(0);
  });

  it("exposes exact trace membership", () => {
    expect(nodesForTrace("market-spine")).toEqual(new Set(["opt-a", "c1", "c2", "c2e", "c2p", "esl", "c25", "c3"]));
    expect(nodesForTrace("whole-system")).toBeUndefined();
  });

  it("retains the read-only authority envelope", () => {
    expect(atlasProjection.authority_effect).toBe("NONE_PRESENTATION_ONLY");
    expect(atlasProjection.research_console_binding_created).toBe(false);
    expect(atlasProjection.current_pointer_published).toBe(false);
    expect(atlasProjection.presentation_state.authority_effect).toBe("NONE");
  });

  it("exposes every ratified surface and receipted query in graph and table form", () => {
    expect(atlasProjection.surface_definitions.map((surface) => surface.id)).toEqual(["architecture", "research", "execution", "authority", "repository", "history"]);
    expect(atlasProjection.query_definitions.map((query) => query.id)).toEqual(["SEARCH", "TRACE", "DEPENDENCY", "IMPACT", "EXPLAIN", "AUTHORITY", "OWNERSHIP", "WHY_BLOCKED", "HISTORY", "DIFF"]);
    expect(atlasProjection.query_definitions.every((query) => query.representations.join("/") === "GRAPH/TABLE")).toBe(true);
  });

  it("uses one deterministic result set for graph and table projections", () => {
    for (const surface of atlasProjection.surface_definitions) {
      for (const query of atlasProjection.query_definitions) {
        const state = defaultWorkbenchState(surface.id);
        const result = projectWorkbenchQuery({ surfaceId: surface.id, family: query.id, selectedId: state.selectedId, traceId: state.traceId, search: "c2e" });
        expect([...result.edgeIds].every((edgeId) => {
          const edge = atlasProjection.edges.find((candidate) => candidate.id === edgeId)!;
          return result.nodeIds.has(edge.source) && result.nodeIds.has(edge.target);
        })).toBe(true);
      }
    }
  });

  it("round-trips typed deep links and fails closed on invalid context", () => {
    const state = { ...defaultWorkbenchState("repository"), queryFamily: "EXPLAIN" as const, viewMode: "table" as const, selectedId: "c2e-module", tab: "Evidence" as const, search: "bridge", authorityVisible: false };
    expect(parseWorkbenchState(serializeWorkbenchState(state))).toEqual(state);
    const invalid = parseWorkbenchState("?surface=write&query=MUTATE&node=unknown&tab=Delete&authority=1");
    expect(invalid).toEqual(defaultWorkbenchState("architecture"));
  });

  it("binds CURRENT reality, L4 drill-down, and the full Inspector contract", () => {
    expect(atlasProjection.reality_class).toBe("CURRENT");
    expect(atlasProjection.nodes.some((node) => node.depth === 4)).toBe(true);
    expect(atlasProjection.inspector_tabs).toEqual(["Overview", "Relations", "Implementation", "Authority", "Evidence", "History"]);
    expect(atlasProjection.deep_link_contract.source_mutation_effect).toBe("NONE");
  });
});
