/**
 * @file tests/unit/members/personStatus.test.ts
 * @brief statusOf: online, last seen, unknown.
 */
import { describe, it, expect } from "vitest";
import { statusOf } from "@/components/members/personStatus";

describe("statusOf", () => {
  it("prefers online", () => {
    expect(statusOf({ online: true, last_seen_at: null })).toBe("Online now");
  });
  it("uses relative last seen", () => {
    const iso = new Date(Date.now() - 3 * 3600_000).toISOString();
    expect(statusOf({ online: false, last_seen_at: iso })).toBe(
      "Active 3h ago",
    );
  });
  it("is empty when unknown", () => {
    expect(statusOf({ online: false, last_seen_at: null })).toBe("");
  });
});
