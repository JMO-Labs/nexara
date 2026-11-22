/**
 * @file tests/unit/mentions/groupTags.test.tsx
 * @brief @group tags: picker eligibility and the rendered group chip.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import type { Subgroup } from "@/lib/api/subgroups";

vi.mock("@/hooks/useMembersList", async (orig) => ({
  ...(await orig<object>()),
  useMembersList: () => ({
    data: [
      { id: "u1", username: "ruth", display_name: "Ruth", avatar_url: null },
    ],
  }),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({
    data: [{ id: "g1", slug: "book-club", name: "Book club" }],
  }),
}));

import { taggableGroups } from "@/hooks/useTaggableGroups";
import { Markdown } from "@/components/ui/Markdown";

const g = (p: Partial<Subgroup>) =>
  ({
    id: "g",
    slug: "s",
    name: "S",
    avatar_url: null,
    is_member: true,
    archived_at: null,
    my_role: "member",
    tag_policy: "members",
    ...p,
  }) as Subgroup;

describe("taggableGroups", () => {
  it("keeps groups the viewer may tag", () => {
    const out = taggableGroups([
      g({ id: "a", slug: "ok" }),
      g({ id: "b", is_member: false }),
      g({ id: "c", tag_policy: "admins" }),
      g({ id: "d", tag_policy: "admins", my_role: "moderator", slug: "mods" }),
      g({ id: "e", archived_at: "2026-01-01" }),
    ]);
    expect(out.map((x) => x.username)).toEqual(["ok", "mods"]);
    expect(out[0]).toMatchObject({ id: "g:a", hint: "Group" });
  });
});

describe("Markdown mentions", () => {
  it("renders group slugs as group chips and people as profile links", () => {
    renderWithProviders(
      <Markdown content="Hi @book-club and @ruth" mentions />,
    );
    expect(
      screen.getByRole("link", { name: "Book club group" }),
    ).toHaveAttribute("href", "/app/subgroups/book-club");
    expect(screen.getByRole("link", { name: "@ruth" })).toHaveAttribute(
      "href",
      "/app/u/ruth",
    );
  });
});
