import { test, expect } from '@playwright/test';
import { login } from './fixtures/auth';

test('user can RSVP to an event', async ({ page }) => {
  await login(page);
  await page.goto('/app/events');
  const card = page.getByTestId('event-card').first();
  await expect(card).toBeVisible();
  await card.getByRole('button', { name: /going|rsvp/i }).click();
  await expect(card.getByText(/going/i)).toBeVisible();
});
