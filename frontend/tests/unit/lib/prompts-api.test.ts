/**
 * @file tests/unit/lib/prompts-api.test.ts
 * @brief Verify prompts API client hits backend /api/v1/prompts routes.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
  seg: (v: string) => encodeURIComponent(v),
}));

import { apiGet, apiPost, apiPatch, apiPut, apiDelete } from "@/lib/api/client";
import * as prompts from "@/lib/api/prompts";
import {
  listPrompts,
  createPrompt,
  updatePrompt,
  deletePrompt,
  type PromptCreate,
} from "@/lib/api/prompts";

describe("prompts API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listPrompts GETs /api/v1/prompts", async () => {
    await listPrompts();
    expect(apiGet).toHaveBeenCalledWith("/api/v1/prompts");
  });

  it("createPrompt POSTs /api/v1/prompts with backend fields", async () => {
    const payload: PromptCreate = {
      title: "T",
      body: "B",
      frequency_type: "weekly",
      trigger_weekday: 2,
      active_days: 7,
    };
    await createPrompt(payload);
    expect(apiPost).toHaveBeenCalledWith("/api/v1/prompts", payload);
  });

  it("updatePrompt PATCHes /api/v1/prompts/{id}", async () => {
    await updatePrompt("p 1", { is_enabled: false });
    expect(apiPatch).toHaveBeenCalledWith("/api/v1/prompts/p%201", {
      is_enabled: false,
    });
    expect(apiPut).not.toHaveBeenCalled();
  });

  it("deletePrompt DELETEs /api/v1/prompts/{id}", async () => {
    await deletePrompt("p1");
    expect(apiDelete).toHaveBeenCalledWith("/api/v1/prompts/p1");
  });

  it("does not expose seedBuiltinPrompts", () => {
    expect("seedBuiltinPrompts" in prompts).toBe(false);
  });
});
