/**
 * @file tests/e2e/search.spec.ts
 * @brief Command palette opens via keyboard and lists suggestions.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("command palette returns results for a query", async ({ page }) => {
  await login(page);
  await page.goto("/app");
  const input = page.getByRole("combobox", { name: "Command palette" });
  // The shortcut is ignored until the app hydrates; retry the keypress.
  await expect(async () => {
    await page.keyboard.press("ControlOrMeta+K");
    await expect(input).toBeVisible({ timeout: 1_500 });
  }).toPass({ timeout: 15_000 });
  await input.fill("chat");
  await expect(page.getByRole("option").first()).toBeVisible();
  await page.getByRole("option", { name: /Chat/ }).first().click();
  await expect(page).toHaveURL(/\/app\/chat/);
});
