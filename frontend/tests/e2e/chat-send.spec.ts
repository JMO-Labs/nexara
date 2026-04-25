import { test, expect } from '@playwright/test';
import { login } from './fixtures/auth';

test('user can send a chat message', async ({ page }) => {
  await login(page);
  await page.goto('/app/chat');
  await page.getByRole('link', { name: /general|#/i }).first().click();
  const body = `e2e chat ${Date.now()}`;
  await page.getByRole('textbox', { name: /message|chat/i }).fill(body);
  await page.keyboard.press('Enter');
  await expect(page.getByText(body)).toBeVisible();
});
