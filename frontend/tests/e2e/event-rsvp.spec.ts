/**
 * @file tests/e2e/event-rsvp.spec.ts
 * @brief RSVP "Going" to the next upcoming event from the details drawer.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can RSVP to an event", async ({ page }) => {
  await login(page);
  await page.goto("/app/events");
  const item = page
    .getByRole("complementary", { name: "Event list" })
    .getByRole("button")
    .first();
  const drawer = page.getByRole("region", { name: "Event details" });
  // Retry the click: it can land before React hydrates the list.
  await expect(async () => {
    await item.click();
    await expect(drawer).toBeVisible({ timeout: 1_500 });
  }).toPass({ timeout: 15_000 });
  const rsvp = page.getByRole("group", { name: "RSVP" });
  const going = rsvp.getByRole("button", { name: /^Going/ });
  // Start from a non-Going state so reruns on the same DB are idempotent.
  if ((await going.getAttribute("aria-pressed")) === "true") {
    await rsvp.getByRole("button", { name: /^Maybe/ }).click();
    await expect(going).toHaveAttribute("aria-pressed", "false");
  }
  await going.click();
  await expect(going).toHaveAttribute("aria-pressed", "true");
});
