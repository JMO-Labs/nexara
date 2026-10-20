import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can save profile settings", async ({ page }) => {
  await login(page);
  await page.goto("/app/settings?tab=profile");
  const display = page.getByLabel(/display name/i);
  const next = `Tester ${Date.now() % 10000}`;
  await display.fill(next);
  await page.getByRole("button", { name: /save/i }).click();
  await expect(page.getByText(/saved|updated/i)).toBeVisible();
});
