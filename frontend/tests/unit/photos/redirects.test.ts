/**
 * @file tests/unit/photos/redirects.test.ts
 * @brief Legacy galleries/media routes redirect into /app/photos.
 */
import { describe, it, expect, vi } from "vitest";

const redirect = vi.fn((url: string) => {
  throw new Error(`REDIRECT:${url}`);
});
vi.mock("next/navigation", () => ({ redirect }));

describe("photos redirects", () => {
  it("/app/galleries -> /app/photos", async () => {
    const { default: Page } = await import("@/app/app/galleries/page");
    await expect(Page({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "REDIRECT:/app/photos",
    );
  });

  it("/app/galleries preserves the query string", async () => {
    const { default: Page } = await import("@/app/app/galleries/page");
    await expect(
      Page({
        searchParams: Promise.resolve({ gallery: "g1", item: ["2"] }),
      }),
    ).rejects.toThrow("REDIRECT:/app/photos?gallery=g1&item=2");
  });

  it("/app/media -> /app/photos?view=all", async () => {
    const { default: Page } = await import("@/app/app/media/page");
    expect(() => Page()).toThrow("REDIRECT:/app/photos?view=all");
  });

  it("/app/galleries/[id] -> /app/photos?gallery=id", async () => {
    const { default: Page } = await import("@/app/app/galleries/[id]/page");
    await expect(
      Page({ params: Promise.resolve({ id: "a b" }) }),
    ).rejects.toThrow("REDIRECT:/app/photos?gallery=a+b");
  });
});
