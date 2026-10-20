import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can create a post from the feed", async ({ page }) => {
  await login(page);
  await page.goto("/app");
  const body = `e2e post ${Date.now()}`;
  await page
    .getByRole("textbox", { name: /what.s on your mind|compose/i })
    .fill(body);
  await page.getByRole("button", { name: /post|publish/i }).click();
  await expect(page.getByText(body)).toBeVisible();
});
