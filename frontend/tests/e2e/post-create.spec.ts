/**
 * @file tests/e2e/post-create.spec.ts
 * @brief Expand the collapsed composer, post to the community feed.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can create a post from the feed", async ({ page }) => {
  await login(page);
  await page.goto("/app");
  const body = `e2e post ${Date.now()}`;
  await page
    .getByRole("button", { name: "Share something with everyone" })
    .click();
  await expect(
    page.getByRole("radiogroup", { name: "Share with" }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "Post composer" }).fill(body);
  await page.getByRole("button", { name: "Post", exact: true }).click();
  await expect(page.getByRole("article").filter({ hasText: body })).toBeVisible(
    { timeout: 10_000 },
  );
});
