import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can react to a post", async ({ page }) => {
  await login(page);
  await page.goto("/app");
  const reactBtn = page.getByRole("button", { name: /react|like|♥/i }).first();
  await expect(reactBtn).toBeVisible();
  await reactBtn.click();
  await expect(reactBtn).toHaveAttribute("aria-pressed", /true|1/);
});
