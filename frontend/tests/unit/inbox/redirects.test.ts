/**
 * @file tests/unit/inbox/redirects.test.ts
 * @brief Legacy notifications/bookmarks/lists index routes redirect into
 *        /app/inbox, preserving other query params.
 */
import { describe, it, expect, vi } from "vitest";

const redirect = vi.fn((url: string) => {
  throw new Error(`REDIRECT:${url}`);
});
vi.mock("next/navigation", () => ({ redirect }));

describe("inbox redirects", () => {
  it("/app/notifications -> /app/inbox", async () => {
    const { default: Page } = await import("@/app/app/notifications/page");
    await expect(Page({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "REDIRECT:/app/inbox",
    );
  });

  it("/app/notifications preserves the query string", async () => {
    const { default: Page } = await import("@/app/app/notifications/page");
    await expect(
      Page({ searchParams: Promise.resolve({ filter: "unread" }) }),
    ).rejects.toThrow("REDIRECT:/app/inbox?filter=unread");
  });

  it("/app/bookmarks -> /app/inbox?view=saved", async () => {
    const { default: Page } = await import("@/app/app/bookmarks/page");
    await expect(Page({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "REDIRECT:/app/inbox?view=saved",
    );
  });

  it("/app/lists -> /app/inbox?view=lists", async () => {
    const { default: Page } = await import("@/app/app/lists/page");
    await expect(Page({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "REDIRECT:/app/inbox?view=lists",
    );
  });

  it("/app/lists preserves other params and sets view", async () => {
    const { default: Page } = await import("@/app/app/lists/page");
    await expect(
      Page({ searchParams: Promise.resolve({ visibility: "community" }) }),
    ).rejects.toThrow("REDIRECT:/app/inbox?visibility=community&view=lists");
  });
});
