/**
 * @file tests/e2e/chat-send.spec.ts
 * @brief Single-user chat: open General from the sidebar, send a message.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can send a chat message", async ({ page }) => {
  await login(page);
  await page.goto("/app/chat");
  const general = page.getByRole("button", { name: /# General/ });
  await expect(async () => {
    await general.click();
    await expect(page).toHaveURL(/\/app\/chat\/[0-9a-f-]+/, { timeout: 2_000 });
  }).toPass({ timeout: 15_000 });
  const body = `e2e chat ${Date.now()}`;
  const send = page.getByRole("button", { name: "Send message" });
  // Composer state can reset while the page hydrates; retry fill + send.
  await expect(async () => {
    await page.getByRole("textbox", { name: "Message" }).fill(body);
    await expect(send).toBeEnabled({ timeout: 1_000 });
    await send.click({ timeout: 2_000 });
  }).toPass({ timeout: 20_000 });
  await expect(page.getByText(body)).toBeVisible();
});
