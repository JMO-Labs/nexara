import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

test("user can log in and reach the app shell", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("navigation")).toBeVisible();
});
