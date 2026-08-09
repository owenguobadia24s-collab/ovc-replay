import { afterEach, describe, expect, it, vi } from "vitest";
import { FixtureBoundaryError, getIdentity, requireFixtureEnvelope } from "./client";
import type { ReadEnvelope, SourceIdentity } from "./types";

const identity: SourceIdentity = { commit: "fixture-commit", release_id: "fixture-release", contract_ids: [], schema_ids: [], logical_hashes: [] };
function envelope(): ReadEnvelope<SourceIdentity> { return { fixture_banner: { mode: "FIXTURE_ONLY", data_classification: "SYNTHETIC_FIXTURE", evidence_status: "NON_EVIDENTIARY", authority_effect: "NONE" }, schema_id: "fixture/v1", resource: "identity", source_identity: identity, capability: { capability_id: "SYSTEM", available: true, authorised: true, active: false, authority_effect: "NONE" }, payload: identity }; }

afterEach(() => vi.restoreAllMocks());

describe("fixture API boundary", () => {
  it("accepts only the persistent synthetic non-evidentiary banner", () => {
    expect(requireFixtureEnvelope(envelope()).fixture_banner.mode).toBe("FIXTURE_ONLY");
    const unsafe = envelope() as unknown as { fixture_banner: { mode: string; data_classification: string; evidence_status: string; authority_effect: string } };
    unsafe.fixture_banner.mode = "REAL";
    expect(() => requireFixtureEnvelope(unsafe as unknown as ReadEnvelope<SourceIdentity>)).toThrowError(FixtureBoundaryError);
  });
  it("performs GET-only fixture reads", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => envelope() });
    vi.stubGlobal("fetch", fetchMock);
    const result = await getIdentity();
    expect(result.payload.commit).toBe("fixture-commit");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/identity", expect.objectContaining({ method: "GET" }));
  });
});
