import { test, expect, type APIRequestContext } from "@playwright/test";
import { login } from "./fixtures/auth";
import { apiContext, uniqueId } from "./fixtures/api";

let api: APIRequestContext;
let eventId: string | undefined;

test.beforeAll(async () => {
  api = await apiContext();
});

test.afterEach(async () => {
  if (eventId) await api.delete(`/api/v1/events/${eventId}`);
  eventId = undefined;
});

test.afterAll(async () => {
  await api.dispose();
});

test("user creates an event, sees it on the month grid and opens details", async ({
  page,
}) => {
  const title = `E2E event ${uniqueId()}`;
  const today = new Date();
  const date = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");

  await login(page);
  await page.goto("/app/events");
  await page
    .getByRole("button", { name: /^(new|create) event$/i })
    .first()
    .click();

  const dialog = page.getByRole("dialog", { name: /new event/i });
  await dialog.getByLabel("Title").fill(title);
  await dialog.getByLabel("Start date").fill(date);
  await dialog.getByLabel("Start time").fill("10:00");
  await dialog.getByLabel("End date").fill(date);
  await dialog.getByLabel("End time").fill("11:00");

  const created = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/events") &&
      r.request().method() === "POST" &&
      r.status() === 201,
  );
  await dialog.getByRole("button", { name: "Create" }).click();
  eventId = ((await (await created).json()) as { id: string }).id;

  const grid = page.getByRole("grid");
  await expect(grid).toBeVisible();
  const chip = grid.getByRole("button", { name: new RegExp(title) });
  await expect(chip).toBeVisible();

  await chip.click();
  const drawer = page.getByRole("region", { name: "Event details" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText(title)).toBeVisible();
});
