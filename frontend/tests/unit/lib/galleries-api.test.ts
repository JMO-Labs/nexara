import { describe, it, expect, vi, beforeEach } from "vitest";

const apiGet = vi.fn().mockResolvedValue({});
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
}));

import { listGalleries } from "@/lib/api/galleries";

describe("listGalleries", () => {
  beforeEach(() => apiGet.mockClear());

  it("sends featured_only for featured", async () => {
    await listGalleries({ featured: true });
    expect(apiGet).toHaveBeenCalledWith("/api/v1/galleries?featured_only=true");
  });

  it("appends event_id, cursor and limit", async () => {
    await listGalleries({ event_id: "e1", cursor: "c1", limit: 20 });
    const url = apiGet.mock.calls[0][0] as string;
    const qs = new URLSearchParams(url.split("?")[1]);
    expect(qs.get("event_id")).toBe("e1");
    expect(qs.get("cursor")).toBe("c1");
    expect(qs.get("limit")).toBe("20");
  });

  it("omits query when no params", async () => {
    await listGalleries();
    expect(apiGet).toHaveBeenCalledWith("/api/v1/galleries");
  });
});
