/**
 * @file tests/e2e/notifications.spec.ts
 * @brief Notification e2e flows:
 *        - mention by user B notifies user A: bell badge, unread item, ack.
 *        - bell: trigger notif -> badge 1 -> click navigates -> gone.
 *          Requires the backend to run with APP_ENV=test (test-only
 *          /api/v1/_test/notify endpoint).
 */
import {
  test,
  expect,
  type APIRequestContext,
  type Browser,
} from "@playwright/test";
import { login } from "./fixtures/auth";
import { createSecondUser } from "./fixtures/second-user";

/** @brief B mentions fresh user A; A acks the row. Optionally checks badge. */
async function mentionFlow(
  browser: Browser,
  request: APIRequestContext,
  checkBadgeCleared: boolean,
): Promise<void> {
  const a = await createSecondUser(browser, request, "ea");
  const b = await createSecondUser(browser, request, "eb");
  try {
    await a.page.goto("/app");
    await expect(
      a.page.getByRole("button", { name: "Notifications" }),
    ).toBeVisible();

    await b.page.goto("/app");
    await b.page
      .getByRole("button", { name: "Share something with everyone" })
      .click();
    await b.page
      .getByRole("textbox", { name: "Post composer" })
      .fill(`hello @${a.username} ${Date.now()}`);
    await b.page.getByRole("button", { name: "Post", exact: true }).click();

    const bell = a.page.getByRole("button", {
      name: "Notifications, 1 unread",
    });
    await expect(async () => {
      await a.page.reload();
      await expect(bell).toBeVisible({ timeout: 2_000 });
    }).toPass({ timeout: 20_000 });

    await bell.click();
    const drawer = a.page.getByRole("dialog", { name: "Notifications" });
    // Ack button renders only on unread rows (see NotifRow.test.tsx).
    const ack = drawer.getByRole("button", {
      name: "Acknowledge notification",
    });
    await expect(ack).toHaveCount(1);

    await ack.first().click();
    await expect(ack).toHaveCount(0);
    if (checkBadgeCleared) await expect(bell).toHaveCount(0);
  } finally {
    await a.context.close();
    await b.context.close();
  }
}

test("mention notifies recipient and can be marked read", async ({
  browser,
  request,
}) => {
  await mentionFlow(browser, request, false);
});

// Backend bug: POST /notifications/{id}/dismiss sets dismissed_at but
// dismissed rows.
test("acknowledging a mention clears the unread badge", async ({
  browser,
  request,
}) => {
  await mentionFlow(browser, request, true);
});

test("bell: notification shows, navigates on click, then disappears", async ({
  page,
}) => {
  await login(page);
  await page.goto("/app");

  const res = await page.request.post("/api/v1/_test/notify", {
    data: {
      type: "system",
      payload: { message: "E2E bell ping", link: "/app/settings" },
    },
  });
  test.skip(
    res.status() === 404,
    "needs backend APP_ENV=test (/api/v1/_test/notify); absent in prod image",
  );
  expect(res.ok()).toBeTruthy();

  const bell = page.getByRole("button", { name: /notifications/i }).first();
  await expect(page.getByTestId("unread-badge")).toHaveText("1");
  await expect(bell).toHaveAttribute("aria-label", /1 unread/);

  await bell.click();
  await page.getByText("E2E bell ping").click();
  await expect(page).toHaveURL(/\/app\/settings/);

  await bell.click();
  await expect(page.getByText("E2E bell ping")).toHaveCount(0);
});
