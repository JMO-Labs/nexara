/**
 * @file tests/unit/feed/activePrompts.test.ts
 * @brief API wrappers for active prompts and prompt post fetch.
 */
import { vi, describe, it, expect } from "vitest";

const get = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<object>()),
  apiGet: get,
}));

import { getActivePrompts, getPromptPost } from "@/lib/api/prompts";

describe("prompts api", () => {
  it("getActivePrompts calls /prompts/active", async () => {
    get.mockResolvedValue([]);
    await getActivePrompts();
    expect(get).toHaveBeenCalledWith("/api/v1/prompts/active");
  });
  it("getPromptPost calls /prompts/posts/{id}", async () => {
    await getPromptPost("abc");
    expect(get).toHaveBeenCalledWith("/api/v1/prompts/posts/abc");
  });
});
