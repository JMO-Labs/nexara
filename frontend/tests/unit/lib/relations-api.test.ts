/**
 * @file tests/unit/lib/relations-api.test.ts
 * @brief Relations client hits absolute /api/v1/relations paths.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
  seg: (v: string) => encodeURIComponent(v),
}));

import { apiDelete, apiGet, apiPost } from "@/lib/api/client";
import {
  confirmRelation,
  listRelationRequests,
  listRelations,
  removeRelation,
  requestRelation,
} from "@/lib/api/relations";

describe("relations API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses /api/v1 prefixed paths", async () => {
    await listRelations("u1");
    await listRelations();
    await listRelationRequests();
    await requestRelation({ to_user_id: "u1", kind: "parent" });
    await confirmRelation("r1");
    await removeRelation("r1");
    const paths = [
      ...vi.mocked(apiGet).mock.calls,
      ...vi.mocked(apiPost).mock.calls,
      ...vi.mocked(apiDelete).mock.calls,
    ].map((c) => c[0]);
    expect(paths).toEqual([
      "/api/v1/relations?user_id=u1",
      "/api/v1/relations",
      "/api/v1/relations/requests",
      "/api/v1/relations",
      "/api/v1/relations/r1/confirm",
      "/api/v1/relations/r1",
    ]);
    expect(paths.every((p) => p.startsWith("/api/v1/"))).toBe(true);
  });
});
