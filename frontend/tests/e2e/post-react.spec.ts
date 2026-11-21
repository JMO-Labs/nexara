/**
 * @file tests/e2e/post-react.spec.ts
 * @brief Pick a reaction from the picker and see the post's count update.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can react to a post", async ({ page }) => {
  await login(page);
  await page.goto("/app");
  const post = page.getByRole("article").first();
  const before = (await post.getAttribute("aria-label")) ?? "";
  await post.getByRole("button", { name: "Add reaction" }).click();
  await post.getByRole("button", { name: "React 🎉" }).click();
  await expect(post).not.toHaveAttribute("aria-label", before);
  await expect(post).toHaveAttribute("aria-label", /\d+ reactions?/);
});
