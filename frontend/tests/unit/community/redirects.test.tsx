/**
 * @file tests/unit/community/redirects.test.tsx
 * @brief Legacy /app/members and /app/subgroups index routes redirect to Community.
 */
import { describe, it, expect, vi } from "vitest";

vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    throw new Error(`REDIRECT:${url}`);
  },
}));

import MembersIndex from "@/app/app/members/page";
import SubgroupsIndex from "@/app/app/subgroups/page";

describe("legacy community redirects", () => {
  it("/app/members goes to /app/community", async () => {
    await expect(
      MembersIndex({ searchParams: Promise.resolve({}) }),
    ).rejects.toThrow("REDIRECT:/app/community");
  });

  it("/app/members keeps the query string", async () => {
    await expect(
      MembersIndex({ searchParams: Promise.resolve({ user: "u1" }) }),
    ).rejects.toThrow("REDIRECT:/app/community?user=u1");
  });

  it("/app/subgroups goes to the groups view", async () => {
    await expect(
      SubgroupsIndex({ searchParams: Promise.resolve({}) }),
    ).rejects.toThrow("REDIRECT:/app/community?view=groups");
  });

  it("/app/subgroups merges view=groups over an existing view and keeps other params", async () => {
    await expect(
      SubgroupsIndex({
        searchParams: Promise.resolve({ view: "people", q: "choir" }),
      }),
    ).rejects.toThrow("REDIRECT:/app/community?view=groups&q=choir");
  });
});
