/**
 * @file e2e/smoke.spec.ts
 * @brief Smoke test to verify the app loads and renders the landing page.
 */

import { test, expect } from "@playwright/test";

test("landing page loads and shows heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
});
