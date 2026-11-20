/**
 * @file tests/e2e/people-directory.spec.ts
 * @brief /app/community (People view): search finds a freshly registered user by username and
 *        the Profile button opens their profile page.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { createSecondUser } from "./fixtures/second-user";

test("search finds the second user and opens their profile", async ({
  page,
  browser,
  request,
}) => {
  test.setTimeout(90_000);
  const other = await createSecondUser(browser, request, "ep");
  try {
    await login(page);
    await page.goto("/app/community");
    await page
      .getByRole("searchbox", { name: "Search people" })
      .fill(other.username);

    // Username search matches exactly one person; the card shows the display
    // name (the @handle is replaced by presence text for online users).
    const card = page.getByRole("list").getByRole("article");
    await expect(card).toHaveCount(1);
    await expect(card.getByRole("heading", { level: 3 })).toHaveText(/E2E ep/);

    await card.getByRole("button", { name: /profile$/ }).click();
    await expect(page).toHaveURL(/\/app\/members\/[0-9a-f-]+/);
    await expect(
      page
        .getByRole("main")
        .getByRole("heading", { name: /E2E ep/ })
        .first(),
    ).toBeVisible();
  } finally {
    await other.context.close();
  }
});
