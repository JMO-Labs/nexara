/**
 * @file tests/e2e/phone-unified.spec.ts
 * @brief Phone viewport (390x844): Home accordion keeps exactly one tile open,
 *        bottom tab bar navigates, and the More sheet lists/opens Groups.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

test("home accordion opens one tile at a time", async ({ page }) => {
  await login(page);
  const headers = page.locator("[data-tile] > button[aria-expanded]");
  const open = page.locator('[data-tile] > button[aria-expanded="true"]');
  await expect(headers).toHaveCount(4);
  await expect(open).toHaveCount(1);

  for (let i = 0; i < 4; i++) {
    const h = headers.nth(i);
    await expect(async () => {
      if ((await h.getAttribute("aria-expanded")) !== "true") await h.tap();
      await expect(h).toHaveAttribute("aria-expanded", "true", {
        timeout: 1_500,
      });
    }).toPass({ timeout: 15_000 });
    await expect(open).toHaveCount(1);
  }
});

test("bottom tab bar navigates between sections", async ({ page }) => {
  await login(page);
  const nav = page.getByRole("navigation", { name: "Primary" });
  const targets: [string, RegExp][] = [
    ["Chat", /\/app\/chat/],
    ["Calendar", /\/app\/events/],
    ["Photos", /\/app\/photos/],
    ["Home", /\/app$/],
  ];
  for (const [name, url] of targets) {
    const link = nav.getByRole("link", { name });
    await expect(async () => {
      await link.tap();
      await expect(page).toHaveURL(url, { timeout: 1_500 });
    }).toPass({ timeout: 15_000 });
    await expect(link).toHaveAttribute("aria-current", "page");
  }
});

test("More sheet contains Groups and navigates to it", async ({ page }) => {
  await login(page);
  const sheet = page.getByRole("dialog", { name: "More" });
  await expect(async () => {
    await page.getByRole("button", { name: "More" }).tap();
    await expect(sheet).toBeVisible({ timeout: 1_500 });
  }).toPass({ timeout: 15_000 });
  for (const name of ["Groups", "People", "Settings"]) {
    await expect(sheet.getByRole("link", { name })).toBeVisible();
  }
  await sheet.getByRole("link", { name: "Groups" }).tap();
  await expect(page).toHaveURL(/\/app\/subgroups/);
  await expect(sheet).toBeHidden();
});
