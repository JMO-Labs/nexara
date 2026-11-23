/**
 * @file tests/unit/lib/tree/api.test.ts
 * @brief Tree API client paths start with /api/v1/.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiGet: (...a: unknown[]) => apiGet(...a),
  seg: (s: string) => encodeURIComponent(s),
}));

import { getFamilyTree, getGroupTree } from "@/lib/api/tree";

describe("tree api paths", () => {
  beforeEach(() => apiGet.mockReset());

  it("family", async () => {
    await getFamilyTree();
    expect(apiGet).toHaveBeenLastCalledWith("/api/v1/tree/family");
    await getFamilyTree({ root: "r1", gens: 5 });
    expect(apiGet).toHaveBeenLastCalledWith(
      "/api/v1/tree/family?root=r1&gens=5",
    );
  });

  it("group", async () => {
    await getGroupTree("book club");
    expect(apiGet).toHaveBeenLastCalledWith("/api/v1/tree/group/book%20club");
  });
});
