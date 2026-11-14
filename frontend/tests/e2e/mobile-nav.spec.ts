/**
 * @file tests/e2e/mobile-nav.spec.ts
 * @brief Mobile (390x844, touch) bottom tab bar and More sheet behaviour.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

test("tab bar navigates the main sections", async ({ page }) => {
  await login(page);
  const nav = page.getByRole("navigation", { name: "Primary" });
  for (const name of ["Chat", "Calendar", "Groups", "Home"]) {
    await nav.getByRole("link", { name }).tap();
    await expect(nav.getByRole("link", { name })).toHaveAttribute(
      "aria-current",
      "page",
    );
  }
});

test("More sheet opens and closes by tap and Escape", async ({ page }) => {
  await login(page);
  const more = page
    .getByRole("navigation", { name: "Primary" })
    .getByRole("button", { name: "More" });
  const sheet = page.getByRole("dialog", { name: "More" });

  await more.tap();
  await expect(sheet).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();

  await more.tap();
  await expect(sheet).toBeVisible();
  await sheet.getByRole("button", { name: /close/i }).tap();
  await expect(sheet).toBeHidden();
});
