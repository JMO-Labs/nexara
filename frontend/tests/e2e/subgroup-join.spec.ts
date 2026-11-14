import { test, expect, type APIRequestContext } from "@playwright/test";
import { login } from "./fixtures/auth";
import { apiContext, uniqueId } from "./fixtures/api";

let api: APIRequestContext;
let slug: string | undefined;

test.beforeAll(async () => {
  api = await apiContext();
});

test.afterEach(async () => {
  if (slug) {
    await api.post(`/api/v1/subgroups/${slug}/leave`);
    await api.delete(`/api/v1/subgroups/${slug}/permanent`);
  }
  slug = undefined;
});

test.afterAll(async () => {
  await api.dispose();
});

test("user joins an open subgroup and leaves it again", async ({ page }) => {
  const id = uniqueId();
  const name = `E2E group ${id}`;
  slug = `e2e-group-${id}`;

  const res = await api.post("/api/v1/subgroups", {
    data: { name, slug, join_policy: "open" },
  });
  expect(res.ok()).toBeTruthy();
  // Creator is auto-enrolled; leave so the UI starts from "Join".
  await api.post(`/api/v1/subgroups/${slug}/leave`);

  await login(page);
  await page.goto("/app/subgroups");
  await page.getByRole("searchbox", { name: "Search groups" }).fill(name);

  const card = page
    .getByRole("heading", { name })
    .locator("xpath=ancestor::*[@role='button'][1]");
  await card.getByRole("button", { name: "Join", exact: true }).click();
  await expect(card.getByRole("button", { name: "Leave" })).toBeVisible();

  await card.getByRole("button", { name: "Leave" }).click();
  await expect(
    card.getByRole("button", { name: "Join", exact: true }),
  ).toBeVisible();
});
