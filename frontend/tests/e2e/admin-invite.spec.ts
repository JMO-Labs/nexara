import { test, expect } from '@playwright/test';
import { login } from './fixtures/auth';

test('admin can create an invite', async ({ page }) => {
  await login(page);
  await page.goto('/app/admin?tab=invites');
  await page.getByRole('button', { name: /create invite|new invite/i }).click();
  await page.getByLabel(/email/i).fill(`invite+${Date.now()}@example.com`);
  await page.getByRole('button', { name: /send|create/i }).click();
  await expect(page.getByText(/invite (sent|created)/i)).toBeVisible();
});
