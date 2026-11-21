/**
 * @file tests/e2e/admin-invite.spec.ts
 * @brief Admin creates an invite from the Invites tab and revokes it.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("admin can create an invite", async ({ page }) => {
  const email = `invite+${Date.now()}@example.com`;
  await login(page);
  await page.goto("/app/admin?tab=invites");
  await page.getByRole("textbox", { name: "Email address" }).fill(email);
  await page.getByRole("button", { name: "Send invite" }).click();
  const row = page.getByRole("row", {
    name: new RegExp(email.replace("+", "\\+")),
  });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /Revoke invite/ }).click();
  await expect(row).toHaveCount(0);
});
