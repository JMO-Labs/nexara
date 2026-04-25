/**
 * @file tests/e2e/fixtures/auth.ts
 * @brief Shared login helper. Drives the real /login form so every spec
 *        starts authenticated against the seeded backend account.
 */
import { expect, type Page } from '@playwright/test';

export const E2E_EMAIL = process.env.E2E_USER_EMAIL ?? 'admin@nexara.local';
export const E2E_PASSWORD = process.env.E2E_USER_PASSWORD ?? 'changeme123!';

export async function login(page: Page): Promise<void> {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(E2E_EMAIL);
  await page.getByLabel(/password/i).fill(E2E_PASSWORD);
  await page.getByRole('button', { name: /sign in|log in/i }).click();
  await expect(page).toHaveURL(/\/app/);
}
