import { test, expect } from "@playwright/test";
import { createSecondUser } from "./fixtures/second-user";

test("mention notifies recipient and can be marked read", async ({
  browser,
  request,
}) => {
  const a = await createSecondUser(browser, request, "ea");
  const b = await createSecondUser(browser, request, "eb");
  try {
    await a.page.goto("/app");
    await expect(
      a.page.getByRole("button", { name: "Notifications" }),
    ).toBeVisible();

    await b.page.goto("/app");
    await b.page
      .getByRole("textbox", { name: "Post composer" })
      .fill(`hello @${a.username} ${Date.now()}`);
    await b.page.getByRole("button", { name: /^post$/i }).click();

    const bell = a.page.getByRole("button", {
      name: /Notifications, \d+ unread/,
    });
    await expect(async () => {
      await a.page.reload();
      await expect(bell).toBeVisible({ timeout: 2_000 });
    }).toPass({ timeout: 20_000 });

    await bell.click();
    const drawer = a.page.getByRole("dialog", { name: "Notifications" });
    await expect(drawer.getByRole("img", { name: "Unread" })).toBeVisible();

    await drawer
      .getByRole("button", { name: "Acknowledge notification" })
      .first()
      .click();
    await expect(drawer.getByRole("img", { name: "Unread" })).toHaveCount(0);
  } finally {
    await a.context.close();
    await b.context.close();
  }
});
