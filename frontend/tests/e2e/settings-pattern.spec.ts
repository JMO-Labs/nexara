/**
 * @file tests/e2e/settings-pattern.spec.ts
 * @brief Appearance > Background pattern: a change persists across reload and
 *        is reset to the original choice afterwards.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("background pattern change persists across reload", async ({ page }) => {
  await login(page);
  await page.goto("/app/settings?tab=appearance");
  const group = page.getByRole("radiogroup", { name: "Background pattern" });
  const checked = group.getByRole("radio", { checked: true });
  await expect(checked).toHaveCount(1, { timeout: 15_000 });
  const original =
    (await checked.getAttribute("aria-label")) ??
    (await group.locator("[role=radio][aria-checked=true]").innerText());

  const target = original === "Dots" ? "Waves" : "Dots";
  try {
    const saved = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/settings") &&
        r.request().method() !== "GET" &&
        r.ok(),
    );
    await group.getByRole("radio", { name: target }).click();
    await saved;
    await expect(group.getByRole("radio", { name: target })).toBeChecked();

    await page.reload();
    await expect(
      page
        .getByRole("radiogroup", { name: "Background pattern" })
        .getByRole("radio", { name: target }),
    ).toBeChecked();
  } finally {
    await page
      .getByRole("radiogroup", { name: "Background pattern" })
      .getByRole("radio", { name: original })
      .click();
  }
});
