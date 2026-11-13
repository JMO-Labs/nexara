/**
 * @file tests/e2e/signup-onboarding.spec.ts
 * @brief Registers a fresh user, skips the welcome modal and verifies it
 *        stays dismissed after reload. Unique credentials per run. Assumes
 *        open registration (ENABLE_REGISTRATION=true) on the target stack.
 */
import { randomBytes } from "node:crypto";
import { test, expect } from "@playwright/test";

test("new user registers, skips onboarding, modal stays dismissed", async ({
  page,
}) => {
  const uid = `${Date.now()}${randomBytes(3).toString("hex")}`;
  const username = `e2e_${uid}`;
  const email = `${username}@example.com`;
  const password = randomBytes(9).toString("base64url"); // 12 chars

  await page.goto("/register");
  await page.getByLabel("Display name").fill(`E2E ${uid}`);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/app/);
  const dialog = page.getByRole("dialog", { name: /welcome/i });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Skip for now" }).click();
  await expect(dialog).toBeHidden();

  await page.reload();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.getByRole("navigation").first()).toBeVisible();
  await expect(page.getByRole("dialog", { name: /welcome/i })).toHaveCount(0);
});
