/**
 * @file tests/e2e/photos.spec.ts
 * @brief /app/photos: Albums <-> All photos view switch (URL-synced) and the
 *        header "Upload photos" panel feeding the All photos grid.
 */
import path from "node:path";
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

const FIXTURE = path.join(__dirname, "fixtures", "tiny.png");

test("view switch toggles Albums and All photos", async ({ page }) => {
  await login(page);
  await page.goto("/app/photos");
  const view = page.getByRole("radiogroup", { name: "View" });
  await expect(view.getByRole("radio", { name: "Albums" })).toBeChecked();
  await expect(page.getByRole("list", { name: "Albums" })).toBeVisible();

  await view.getByRole("radio", { name: "All photos" }).click();
  await expect(page).toHaveURL(/view=all/);
  await expect(page.getByRole("list", { name: "All photos" })).toBeVisible();
  await expect(
    page.getByRole("searchbox", { name: "Search photos" }),
  ).toBeVisible();

  await view.getByRole("radio", { name: "Albums" }).click();
  await expect(page.getByRole("list", { name: "Albums" })).toBeVisible();
});

// App bug: "Upload photos" posts to /media/upload, which creates an orphan
// media row that is not in any album, while All photos (GET /home/media)
// only aggregates album items. Remove test.fail() once uploads land there.
test("uploaded photo appears in All photos", async ({ page }) => {
  test.fail(true, "standalone upload never reaches home/media aggregate");
  await login(page);
  await page.goto("/app/photos?view=all");
  const grid = page.getByRole("list", { name: "All photos" });
  await expect(grid).toBeVisible();
  const before = await grid.getByRole("listitem").count();

  await page.getByRole("button", { name: "Upload photos" }).click();
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Choose files" }).click();
  await (await chooser).setFiles(FIXTURE);
  await expect(page.getByText("Done")).toBeVisible({ timeout: 30_000 });

  await expect(grid.getByRole("listitem")).toHaveCount(before + 1, {
    timeout: 10_000,
  });
});
