/**
 * @file tests/unit/lib/stories-api.test.ts
 * @brief Stories client always hits versioned /api/v1/stories paths.
 */
import { describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
const apiPost = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", () => ({
  apiGet,
  apiPost,
  seg: (v: string | number) => encodeURIComponent(String(v)),
}));

import {
  answerStory,
  askStory,
  declineStory,
  listStoryRequests,
  storyQuestions,
  userStories,
} from "@/lib/api/stories";

describe("stories api paths", () => {
  it("all start with /api/v1/stories", () => {
    listStoryRequests();
    storyQuestions();
    userStories("u1", "2026-01-01T00:00:00Z");
    askStory("u1", "Q?");
    answerStory("r1", "p1");
    declineStory("r1");
    const paths = [...apiGet.mock.calls, ...apiPost.mock.calls].map(
      (c) => c[0] as string,
    );
    expect(paths).toHaveLength(6);
    for (const p of paths) expect(p.startsWith("/api/v1/stories")).toBe(true);
    expect(apiGet).toHaveBeenCalledWith("/api/v1/stories/requests");
    expect(apiPost).toHaveBeenCalledWith("/api/v1/stories/requests/r1/decline");
    expect(apiPost).toHaveBeenCalledWith("/api/v1/stories/requests", {
      teller_id: "u1",
      question: "Q?",
    });
    expect(String(apiGet.mock.calls[2][0])).toContain("cursor=");
  });
});
