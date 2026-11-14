/**
 * @file tests/e2e/notifications.spec.ts
 * @brief Bell flow: trigger notif -> badge 1 -> click navigates -> gone.
 *        Requires the backend to run with APP_ENV=test (test-only
 *        /api/v1/_test/notify endpoint).
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

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
  expect(res.ok()).toBeTruthy();

  const bell = page.getByRole("button", { name: /notifications/i }).first();
  await expect(bell).toContainText("1");

  await bell.click();
  await page.getByText("E2E bell ping").click();
  await expect(page).toHaveURL(/\/app\/settings/);

  await bell.click();
  await expect(page.getByText("E2E bell ping")).toHaveCount(0);
});
