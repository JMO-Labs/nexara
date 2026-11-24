/**
 * @file tests/unit/notifications/pushTag.test.ts
 * @brief pushTag parity with backend channels/push.py; safePath guard.
 */
import { describe, it, expect } from "vitest";
import { pushTag, safePath } from "@/lib/notifications/pushTag";

describe("pushTag", () => {
  it("falls back to type", () => {
    expect(pushTag("system")).toBe("system");
    expect(pushTag("system", { post_id: "" })).toBe("system");
  });
  it("uses first thread key in backend order", () => {
    expect(pushTag("comment", { post_id: "a", channel_id: "b" })).toBe(
      "comment:a",
    );
    expect(pushTag("msg", { channel_id: "c" })).toBe("msg:c");
    expect(pushTag("ev", { event_id: "e" })).toBe("ev:e");
    expect(pushTag("x", { target_id: "t" })).toBe("x:t");
  });
});

describe("safePath", () => {
  it.each([["/app/x"], ["/app?a=1#h"]])("accepts %s", (u) =>
    expect(safePath(u)).toBe(u),
  );
  it.each([
    ["https://evil.com"],
    ["//evil.com"],
    ["/\\evil.com"],
    ["javascript:alert(1)"],
    [undefined],
  ])("rejects %s", (u) => expect(safePath(u)).toBeNull());
});
