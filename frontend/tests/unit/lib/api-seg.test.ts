import { describe, it, expect, vi, afterEach } from "vitest";
import { seg } from "@/lib/api/client";
import { getSubgroup } from "@/lib/api/subgroups";

describe("seg", () => {
  it("encodes", () => {
    expect(seg("a b")).toBe("a%20b");
    expect(seg("../x")).toBe("..%2Fx");
    expect(seg(5)).toBe("5");
  });
  it("rejects empty and dot segments", () => {
    expect(() => seg("..")).toThrow();
    expect(() => seg(".")).toThrow();
    expect(() => seg("")).toThrow();
  });
});

describe("path hardening", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("getSubgroup encodes slug", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response("{}", { headers: { "content-type": "application/json" } }),
      );
    vi.stubGlobal("fetch", fetchMock);
    await getSubgroup("../admin");
    expect(String(fetchMock.mock.calls[0][0])).toContain("..%2Fadmin");
  });
});
