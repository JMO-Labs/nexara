/**
 * @file tests/e2e/lists.spec.ts
 * @brief Lists happy path: create a list in the UI, add two items, complete
 *        one and see the "1/2 done" counter; claim and release a signup
 *        slot and see the remaining quantity drop and recover.
 */
import { test, expect, type APIRequestContext } from "@playwright/test";
import { login } from "./fixtures/auth";
import { apiContext, uniqueId } from "./fixtures/api";

const LISTS = "/api/v1/lists";

let api: APIRequestContext;
let listIds: string[] = [];

test.beforeAll(async () => {
  api = await apiContext();
});

test.afterEach(async () => {
  for (const id of listIds) await api.delete(`${LISTS}/${id}`);
  listIds = [];
});

test.afterAll(async () => {
  await api.dispose();
});

/**
 * @brief Remaining signup slots of one item, read back from the API.
 * @param listId parent list
 * @param itemId item to read
 * @return signup_quantity_needed
 */
async function remaining(listId: string, itemId: string): Promise<number> {
  const res = await api.get(`${LISTS}/${listId}/items`);
  expect(res.ok()).toBeTruthy();
  const { items } = (await res.json()) as {
    items: { id: string; signup_quantity_needed: number | null }[];
  };
  const item = items.find((i) => i.id === itemId);
  expect(item).toBeDefined();
  return item?.signup_quantity_needed ?? 0;
}

test("user creates a list, adds two items and completes one", async ({
  page,
}) => {
  const title = `E2E list ${uniqueId()}`;
  await login(page);
  await page.goto("/app/lists");
  await page.getByRole("link", { name: "New list" }).click();

  const dialog = page.getByRole("dialog", { name: "New list" });
  await dialog.getByLabel("Title").fill(title);
  const created = page.waitForResponse(
    (r) =>
      r.url().endsWith(LISTS) &&
      r.request().method() === "POST" &&
      r.status() === 201,
  );
  await dialog.getByRole("button", { name: "Create", exact: true }).click();
  const listId = ((await (await created).json()) as { id: string }).id;
  listIds.push(listId);

  await page.goto(`/app/lists/${listId}`);
  await page.getByRole("button", { name: "Add item" }).click();
  await page
    .getByRole("dialog", { name: "New item" })
    .getByRole("button", { name: "Save" })
    .click();
  await expect(
    page.getByRole("checkbox", { name: "Complete Item 1" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "New item" }).click();
  await page
    .getByRole("dialog", { name: "New item" })
    .getByRole("button", { name: "Save" })
    .click();
  await expect(
    page.getByRole("checkbox", { name: "Complete Item 2" }),
  ).toBeVisible();

  const completed = page.waitForResponse(
    (r) => r.url().endsWith("/complete") && r.request().method() === "POST",
  );
  await page.getByRole("checkbox", { name: "Complete Item 1" }).click();
  expect((await completed).ok()).toBeTruthy();

  await page.goto("/app/lists");
  const card = page
    .locator("div")
    .filter({ has: page.getByRole("button", { name: title }) })
    .filter({ hasText: /\d+\/\d+ done/ })
    .last();
  await expect(card.getByText("1/2 done")).toBeVisible();
});

test("user claims a signup slot and releases it", async () => {
  const res = await api.post(LISTS, {
    data: {
      title: `E2E signup ${uniqueId()}`,
      field_schema: [
        {
          key: "slots",
          label: "Slots",
          type_key: "signup",
          config: { default_quantity_needed: 3 },
        },
      ],
    },
  });
  expect(res.status()).toBe(201);
  const listId = ((await res.json()) as { id: string }).id;
  listIds.push(listId);

  const itemRes = await api.post(`${LISTS}/${listId}/items`, {
    data: { position: 0, values: { slots: 3 } },
  });
  expect(itemRes.status()).toBe(201);
  const itemId = ((await itemRes.json()) as { id: string }).id;
  const signups = `${LISTS}/${listId}/items/${itemId}/signups`;

  expect(await remaining(listId, itemId)).toBe(3);

  const claim = await api.post(signups, { data: { quantity: 1 } });
  expect(claim.status()).toBe(201);
  expect(await remaining(listId, itemId)).toBe(2);

  const release = await api.delete(signups);
  expect(release.status()).toBe(204);
  expect(await remaining(listId, itemId)).toBe(3);
});
