/**
 * @file tests/e2e/fixtures/second-user.ts
 * @brief Creates an extra user through the real invite flow: the seeded
 *        admin calls POST /admin/invites, then the invitee registers via
 *        /register?invite=<token> in its own browser context.
 */
import {
  expect,
  type APIRequestContext,
  type Browser,
  type BrowserContext,
  type Page,
} from "@playwright/test";
import { E2E_EMAIL, E2E_PASSWORD } from "./auth";

export interface E2EUser {
  username: string;
  email: string;
  password: string;
  context: BrowserContext;
  page: Page;
}

/** @brief Raw invite token for `email`, created as the seeded admin. */
async function createInvite(
  request: APIRequestContext,
  email: string,
): Promise<string> {
  const login = await request.post("/api/v1/auth/login", {
    data: { email: E2E_EMAIL, password: E2E_PASSWORD },
  });
  expect(login.ok()).toBeTruthy();
  const { access_token } = await login.json();
  const res = await request.post("/api/v1/admin/invites", {
    headers: { Authorization: `Bearer ${access_token}` },
    data: { email, role: "member" },
  });
  expect(res.status()).toBe(201);
  return (await res.json()).raw_token as string;
}

/**
 * @brief Invite and register a fresh user in a new browser context.
 * @param browser Playwright browser.
 * @param request Request context used for the admin invite call.
 * @param prefix Username prefix (letters, digits, _ and - only).
 * @return The registered, signed-in user. Caller closes `context`.
 */
export async function createSecondUser(
  browser: Browser,
  request: APIRequestContext,
  prefix = "e2e",
): Promise<E2EUser> {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const username = `${prefix}${stamp}`;
  const email = `${username}@example.com`;
  const password = "e2e-Passw0rd-123!";
  const token = await createInvite(request, email);

  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`/register?invite=${encodeURIComponent(token)}`);
  await page.getByLabel("Display name").fill(`E2E ${prefix}`);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page
    .getByRole("button", { name: /create account|sign up|register/i })
    .click();
  await expect(page).toHaveURL(/\/app/);
  return { username, email, password, context, page };
}
