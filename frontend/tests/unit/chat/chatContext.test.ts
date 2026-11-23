/**
 * @file tests/unit/chat/chatContext.test.ts
 * @brief Context client hits /api/v1 path; formatters behave.
 */
import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiGet: vi.fn().mockResolvedValue({ kind: "group" }),
}));

import { apiGet } from "@/lib/api/client";
import { getChatContext } from "@/lib/api/chatContext";
import { agoShort, inDays, presenceText } from "@/components/chat/format";

describe("chat context api", () => {
  it("uses /api/v1/chat/channels/{id}/context", async () => {
    await getChatContext("abc");
    expect(apiGet).toHaveBeenCalledWith("/api/v1/chat/channels/abc/context");
  });
});

describe("format", () => {
  const now = new Date("2026-11-22T12:00:00Z");
  it("agoShort", () => {
    expect(agoShort("2026-11-22T11:59:30Z", now)).toBe("now");
    expect(agoShort("2026-11-22T11:55:00Z", now)).toBe("5m");
    expect(agoShort("2026-11-22T10:00:00Z", now)).toBe("2h");
    expect(agoShort("2026-11-20T12:00:00Z", now)).toBe("2d");
  });
  it("presenceText", () => {
    expect(presenceText(true, null, now)).toBe("Online");
    expect(presenceText(false, "2026-11-22T10:00:00Z", now)).toBe(
      "Active 2h ago",
    );
    expect(presenceText(false, null, now)).toBeNull();
  });
  it("inDays", () => {
    expect(inDays(0)).toBe("today");
    expect(inDays(1)).toBe("tomorrow");
    expect(inDays(5)).toBe("in 5 days");
  });
});

import {
  DETAILS_KEY,
  readDetailsPref,
} from "@/components/chat/chat-layout/useDetails";

describe("details preference", () => {
  it("reads the remembered choice from nexara.chat.details", () => {
    expect(DETAILS_KEY).toBe("nexara.chat.details");
    window.localStorage.removeItem(DETAILS_KEY);
    expect(readDetailsPref()).toBeNull();
    window.localStorage.setItem(DETAILS_KEY, "closed");
    expect(readDetailsPref()).toBe(false);
    window.localStorage.removeItem(DETAILS_KEY);
  });
});
