import path from "node:path";
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

const FIXTURE = path.join(__dirname, "fixtures", "tiny.png");

test("user can create a gallery, upload an image and open the lightbox", async ({
  page,
}) => {
  const title = `e2e gallery ${Date.now()}`;
  await login(page);
  await page.goto("/app/galleries");

  await page.getByRole("button", { name: "New gallery" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByRole("button", { name: "Create" }).click();

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
