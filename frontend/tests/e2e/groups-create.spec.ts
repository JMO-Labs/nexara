/**
 * @file tests/e2e/groups-create.spec.ts
 * @brief Create a group through the "New group" dialog, then a second user
 *        joins and leaves it from the Groups page. Group is deleted after.
 */
import { test, expect, type APIRequestContext } from "@playwright/test";
import { login } from "./fixtures/auth";
import { apiContext } from "./fixtures/api";
import { createSecondUser } from "./fixtures/second-user";

let api: APIRequestContext;
let slug: string | undefined;

test.beforeAll(async () => {
  api = await apiContext();
});

test.afterEach(async () => {
  if (slug) await api.delete(`/api/v1/subgroups/${slug}/permanent`);
  slug = undefined;
});

test.afterAll(async () => {
  await api.dispose();
});

test("create a group, then another user joins and leaves it", async ({
  page,
  browser,
  request,
}) => {
  test.setTimeout(90_000);
  const name = `E2E circle ${Date.now().toString(36)}`;
  await login(page);
  await page.goto("/app/subgroups");

  const newGroup = page.getByRole("button", { name: "New group" });
  const dialog = page.getByRole("dialog", { name: "New group" });
  await expect(async () => {
    await newGroup.click();
    await expect(dialog).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 15_000 });
  await dialog.getByRole("textbox", { name: "Name" }).fill(name);
  const create = dialog.getByRole("button", { name: "Create", exact: true });
  await expect(create).toBeEnabled();
  const created = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/subgroups") &&
      r.request().method() === "POST" &&
      r.status() === 201,
  );
  await create.click();
  slug = ((await (await created).json()) as { slug: string }).slug;

  const ownCard = page
    .getByRole("article")
    .filter({ has: page.getByRole("heading", { name }) });
  await expect(ownCard.getByRole("button", { name: "Leave" })).toBeVisible();

  const other = await createSecondUser(browser, request, "eg");
  try {
    await other.page.goto("/app/subgroups");
    await other.page
      .getByRole("searchbox", { name: "Search groups" })
      .fill(name);
    const card = other.page
      .getByRole("article")
      .filter({ has: other.page.getByRole("heading", { name }) });
    await card.getByRole("button", { name: "Join", exact: true }).click();
    await expect(card.getByRole("button", { name: "Leave" })).toBeVisible();
    await card.getByRole("button", { name: "Leave" }).click();
    await expect(
      card.getByRole("button", { name: "Join", exact: true }),
    ).toBeVisible();
  } finally {
    await other.context.close();
  }
});
