/**
 * @file tests/e2e/admin-nav.spec.ts
 * @brief Admin side nav reaches Users, Branding, Moderation and Storage; each
 *        page renders its heading, marks its nav link current and shows no
 *        load-failure notice.
 */
import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

const PAGES: {
  link: string;
  url: RegExp;
  heading: string;
  ready?: RegExp;
}[] = [
  { link: "Users", url: /\/app\/admin\?tab=users/, heading: "Users" },
  { link: "Branding", url: /\/app\/admin\?tab=branding/, heading: "Branding" },
  {
    link: "Moderation",
    url: /\/app\/admin\/moderation/,
    heading: "Moderation",
    // Queue loaded: empty state or at least one report row.
    ready: /No pending reports/,
  },
  { link: "Storage", url: /\/app\/admin\/storage/, heading: "Storage" },
];

test("admin side nav reaches Users, Branding, Moderation, Storage", async ({
  page,
}) => {
  await login(page);
  await page.goto("/app/admin");
  const nav = page.getByRole("complementary");
  for (const p of PAGES) {
    const link = nav.getByRole("link", { name: p.link, exact: true });
    await expect(async () => {
      await link.click();
      await expect(page).toHaveURL(p.url, { timeout: 2_000 });
    }).toPass({ timeout: 15_000 });
    await expect(link).toHaveAttribute("aria-current", /page|true/);
    await expect(
      page
        .getByRole("main")
        .getByRole("heading", { level: 2, name: p.heading, exact: true }),
    ).toBeVisible();
    const main = page.getByRole("main");
    if (p.ready) {
      await expect(
        main.getByText(p.ready).or(main.getByRole("listitem").first()),
      ).toBeVisible();
    }
    await expect(main.getByText(/failed to load|couldn.t load/i)).toHaveCount(
      0,
    );
  }
});
