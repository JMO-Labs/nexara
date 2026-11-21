/**
 * @file tests/e2e/settings-save.spec.ts
 * @brief Profile display name save (verified through /users/me). Restores the
 *        original name afterwards so runs are idempotent.
 *
 * Note: ProfileTab does not prefill current values (app gap), so the saved
 * value is verified via the API rather than by reloading the form.
 */
import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { login } from "./fixtures/auth";
import { apiContext } from "./fixtures/api";

const ORIGINAL_NAME = "Admin";

let api: APIRequestContext;

test.beforeAll(async () => {
  api = await apiContext();
});

test.afterAll(async () => {
  await api.dispose();
});

/** @brief Save `name` through the Profile tab; waits for the 200 response. */
async function saveDisplayName(page: Page, name: string): Promise<void> {
  await page.goto("/app/settings?tab=profile");
  const display = page.getByLabel(/display name/i);
  const save = page.getByRole("button", { name: /save/i });
  await expect(async () => {
    await display.fill(name);
    const saved = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/settings/profile") &&
        r.request().method() === "PUT",
      { timeout: 3_000 },
    );
    await save.click();
    expect((await saved).ok()).toBeTruthy();
  }).toPass({ timeout: 20_000 });
}

async function currentName(): Promise<string> {
  const me = await api.get("/api/v1/users/me");
  return ((await me.json()) as { display_name: string }).display_name;
}

test.afterEach(async ({ page }) => {
  await saveDisplayName(page, ORIGINAL_NAME);
});

test("user can save profile settings", async ({ page }) => {
  await login(page);
  const next = `Tester ${Date.now() % 10000}`;
  await saveDisplayName(page, next);
  await expect.poll(currentName).toBe(next);
});
