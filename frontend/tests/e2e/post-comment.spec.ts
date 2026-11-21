/**
 * @file tests/e2e/post-comment.spec.ts
 * @brief Open a post's comment thread and add a comment.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can comment on a post", async ({ page }) => {
  await login(page);
  await page.goto("/app");
  const post = page.getByRole("article").first();
  await post.getByRole("button", { name: "Comments" }).click();
  const body = `e2e comment ${Date.now()}`;
  await post.getByRole("textbox", { name: "Add a comment" }).fill(body);
  await post.getByRole("button", { name: "Send" }).click();
  await expect(post.getByText(body)).toBeVisible();
});
