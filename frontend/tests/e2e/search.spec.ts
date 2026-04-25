import { test, expect } from '@playwright/test';
import { login } from './fixtures/auth';

test('command palette returns results for a query', async ({ page }) => {
  await login(page);
  await page.goto('/app');
  await page.keyboard.press('Meta+K');
  const input = page.getByRole('textbox', { name: /search|command/i });
  await input.fill('post');
  await expect(page.getByRole('option').first()).toBeVisible({ timeout: 5_000 });
});
