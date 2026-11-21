/**
 * @file tests/e2e/chat-realtime.spec.ts
 * @brief Two browser contexts (admin + fresh user): a sent chat message shows
 *        up for the other user without reload, and an inline reply from the
 *        Home "Chats" tile reaches the chat page live.
 */
import { test, expect, type Page } from "@playwright/test";
import { login } from "./fixtures/auth";
import { createSecondUser } from "./fixtures/second-user";

async function openGeneral(page: Page): Promise<void> {
  await page.goto("/app/chat");
  const general = page.getByRole("button", { name: /# General/ });
  await expect(async () => {
    await general.click();
    await expect(page).toHaveURL(/\/app\/chat\/[0-9a-f-]+/, { timeout: 2_000 });
  }).toPass({ timeout: 15_000 });
  await expect(page.getByRole("textbox", { name: "Message" })).toBeVisible();
}

/** @brief Type into the composer (retrying until hydrated) and send. */
async function sendMessage(page: Page, body: string): Promise<void> {
  const send = page.getByRole("button", { name: "Send message" });
  await expect(async () => {
    await page.getByRole("textbox", { name: "Message" }).fill(body);
    await expect(send).toBeEnabled({ timeout: 1_000 });
    await send.click({ timeout: 2_000 });
  }).toPass({ timeout: 20_000 });
}

test("message sent by one user appears live for the other", async ({
  page,
  browser,
  request,
}) => {
  test.setTimeout(90_000);
  const other = await createSecondUser(browser, request, "ec");
  try {
    await login(page);
    await openGeneral(page);
    await openGeneral(other.page);

    const body = `live msg ${Date.now()}`;
    await sendMessage(page, body);
    await expect(page.getByText(body)).toBeVisible();
    // No reload on the receiving side.
    await expect(other.page.getByText(body)).toBeVisible({ timeout: 15_000 });
  } finally {
    await other.context.close();
  }
});

test("inline reply from the Home Chats tile reaches the chat page", async ({
  page,
  browser,
  request,
}) => {
  test.setTimeout(90_000);
  const other = await createSecondUser(browser, request, "ed");
  try {
    await login(page);
    await openGeneral(other.page);
    // Seed a message so the tile row has something to expand.
    await sendMessage(other.page, `seed ${Date.now()}`);

    await page.goto("/app");
    const row = page
      .locator('[data-tile="chat"]')
      .getByRole("button", { name: /General/ });
    const reply = page.getByRole("textbox", { name: "Reply to General" });
    await expect(async () => {
      if ((await row.getAttribute("aria-expanded")) !== "true") {
        await row.click();
      }
      await expect(reply).toBeVisible({ timeout: 2_000 });
    }).toPass({ timeout: 15_000 });

    const body = `tile reply ${Date.now()}`;
    await reply.fill(body);
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(other.page.getByText(body)).toBeVisible({ timeout: 15_000 });
  } finally {
    await other.context.close();
  }
});
