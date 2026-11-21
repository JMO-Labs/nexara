/**
 * @file tests/e2e/gallery-upload.spec.ts
 * @brief Photos page album flow: create an album, upload an image into it,
 *        open the lightbox. The album is deleted afterwards.
 */
import path from "node:path";
import { test, expect, type APIRequestContext } from "@playwright/test";
import { login } from "./fixtures/auth";
import { apiContext } from "./fixtures/api";

const FIXTURE = path.join(__dirname, "fixtures", "tiny.png");

let api: APIRequestContext;
let galleryId: string | undefined;

test.beforeAll(async () => {
  api = await apiContext();
});

test.afterEach(async () => {
  if (galleryId) await api.delete(`/api/v1/galleries/${galleryId}`);
  galleryId = undefined;
});

test.afterAll(async () => {
  await api.dispose();
});

test("user can create an album, upload an image and open the lightbox", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const title = `e2e album ${Date.now()}`;
  await login(page);
  await page.goto("/app/photos");

  const created = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/galleries") &&
      r.request().method() === "POST" &&
      r.status() === 201,
  );
  await page.getByRole("button", { name: "New album" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create", exact: true }).click();
  galleryId = ((await (await created).json()) as { id: string }).id;

  await page.getByRole("button", { name: title }).click();

  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Choose files" }).click();
  const chooser = await chooserPromise;
  await chooser.setFiles(FIXTURE);

  const item = page.getByRole("button", { name: /^Item 1$/ });
  await expect(item).toBeVisible({ timeout: 30_000 });
  await item.click();

  const lightbox = page.getByRole("dialog", { name: "Lightbox viewer" });
  await expect(lightbox).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(lightbox).toBeHidden();
});
