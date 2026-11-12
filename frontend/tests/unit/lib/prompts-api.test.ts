/**
 * @file tests/unit/lib/prompts-api.test.ts
 * @brief Prompts admin API client hits the real backend routes.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

import * as client from "@/lib/api/client";
import * as prompts from "@/lib/api/prompts";

describe("prompts api", () => {
  beforeEach(() => vi.clearAllMocks());

  it("listPrompts GETs /api/v1/prompts", async () => {
    await prompts.listPrompts();
    expect(client.apiGet).toHaveBeenCalledWith("/api/v1/prompts");
  });

  it("createPrompt POSTs /api/v1/prompts", async () => {
    const body = { title: "t", body: "b", frequency_type: "weekly" as const };
    await prompts.createPrompt(body);
    expect(client.apiPost).toHaveBeenCalledWith("/api/v1/prompts", body);
  });

  it("updatePrompt PATCHes /api/v1/prompts/:id", async () => {
    await prompts.updatePrompt("p 1", { is_enabled: false });
    expect(client.apiPatch).toHaveBeenCalledWith("/api/v1/prompts/p%201", {
      is_enabled: false,
    });
  });

  it("deletePrompt DELETEs /api/v1/prompts/:id", async () => {
    await prompts.deletePrompt("p1");
    expect(client.apiDelete).toHaveBeenCalledWith("/api/v1/prompts/p1");
  });

  it("no longer exports seedBuiltinPrompts", () => {
    expect("seedBuiltinPrompts" in prompts).toBe(false);
  });
});
