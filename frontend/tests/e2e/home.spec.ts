/**
 * @file tests/e2e/home.spec.ts
 * @brief Home glass bento smoke: desktop tiles + scope, phone accordion + tab bar.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test.describe("desktop", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("shows all four tiles and Everything scope pressed", async ({
    page,
  }) => {
    await login(page);
    for (const name of ["Feed", "Chats", "Up next"]) {
      await expect(page.getByRole("heading", { level: 2, name })).toBeVisible();
    }
    await expect(page.locator('[data-tile="photos"] h2')).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Everything" }),
    ).toHaveAttribute("aria-pressed", "true");
  });
});

test.describe("phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("accordion keeps one section open and tab bar is pinned", async ({
    page,
  }) => {
    await login(page);
    const headers = page.locator("[data-tile] > button[aria-expanded]");
    const expanded = page.locator('[data-tile] > button[aria-expanded="true"]');
    await expect(headers).toHaveCount(4);
    await expect(expanded).toHaveCount(1);

    const chats = page.locator('[data-tile="chat"] > button');
    const next = page.locator('[data-tile="next"] > button');
    const first = (await chats.getAttribute("aria-expanded")) === "true";
    const [open, other] = first ? [chats, next] : [next, chats];

    await other.tap();
    await expect(other).toHaveAttribute("aria-expanded", "true");
    await expect(open).toHaveAttribute("aria-expanded", "false");
    await expect(expanded).toHaveCount(1);

    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav).toBeVisible();
    const box = await nav.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y + box!.height).toBeLessThanOrEqual(844);
    expect(box!.y).toBeGreaterThan(844 - 120);
  });
});
