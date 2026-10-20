import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can comment on a post", async ({ page }) => {
  await login(page);
  await page.goto("/app");
  await page
    .getByRole("button", { name: /comment/i })
    .first()
    .click();
  const body = `e2e comment ${Date.now()}`;
  await page
    .getByPlaceholder(/write a comment|add a comment/i)
    .first()
    .fill(body);
  await page.keyboard.press("Enter");
  await expect(page.getByText(body)).toBeVisible();
});
