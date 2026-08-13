import { afterEach, describe, expect, it, vi } from "vitest";
import { getRepresentationSnapshot } from "./client";
import type { ReadEnvelope, WP5ARepresentationSnapshot } from "./types";

afterEach(() => vi.restoreAllMocks());

describe("WP5A representation client", () => {
  it("performs a GET-only fixture read with null winner authority", async () => {
    const payload = {
      source_preflight: {
        first_new_real_research_source: false,
      },
      presentation_guardrails: {
        default_winner: null,
      },
    } as unknown as WP5ARepresentationSnapshot;
    const envelope = {
      fixture_banner: {
        mode: "FIXTURE_ONLY",
        data_classification: "SYNTHETIC_FIXTURE",
        evidence_status: "NON_EVIDENTIARY",
        authority_effect: "NONE",
      },
      schema_id: "ovc-rcn-rn-wp5a-representation-snapshot/v1",
      resource: "research.representations.snapshot",
      source_identity: {
        commit: "fixture",
        release_id: "fixture",
        contract_ids: [],
        schema_ids: [],
        logical_hashes: [],
      },
      capability: {
        capability_id: "RESEARCH",
        available: true,
        authorised: false,
        active: false,
        authority_effect: "NONE",
      },
      payload,
    } satisfies ReadEnvelope<WP5ARepresentationSnapshot>;
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => envelope,
    });
    vi.stubGlobal("fetch", fetchMock);
    const result = await getRepresentationSnapshot();
    expect(result.payload.source_preflight.first_new_real_research_source).toBe(false);
    expect(result.payload.presentation_guardrails.default_winner).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/research/representations/snapshot",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
