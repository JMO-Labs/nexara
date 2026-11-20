/**
 * @file tests/unit/kudos/kudos-redirect.test.ts
 * @brief /app/kudos redirects to the Home feed Kudos filter.
 */
import { describe, it, expect, vi } from "vitest";

const redirect = vi.fn((url: string) => {
  throw new Error(`REDIRECT:${url}`);
});
vi.mock("next/navigation", () => ({ redirect }));

describe("kudos redirect", () => {
  it("/app/kudos -> /app?feed=kudos", async () => {
    const { default: Page } = await import("@/app/app/kudos/page");
    expect(() => Page()).toThrow("REDIRECT:/app?feed=kudos");
  });
});
