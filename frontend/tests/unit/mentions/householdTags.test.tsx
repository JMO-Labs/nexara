/**
 * @file tests/unit/mentions/householdTags.test.tsx
 * @brief @pet / @family mentions: picker rows and the rendered chip.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import type { HouseholdMember } from "@/lib/api/household";

vi.mock("@/hooks/useMembersList", async (orig) => ({
  ...(await orig<object>()),
  useMembersList: () => ({
    data: [
      { id: "u1", username: "ruth", display_name: "Ruth", avatar_url: null },
    ],
  }),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [] }),
}));
vi.mock("@/hooks/useHousehold", () => ({
  useVisibleHousehold: () => ({
    data: [{ id: "h1", kind: "pet", name: "Biscuit", handle: "biscuit" }],
  }),
}));

import { taggableHousehold } from "@/hooks/useTaggableGroups";
import { Markdown } from "@/components/ui/Markdown";

const m = (p: Partial<HouseholdMember>) =>
  ({
    id: "x",
    kind: "pet",
    name: "X",
    handle: "x",
    species: null,
    relation: null,
    ...p,
  }) as HouseholdMember;

describe("household mentions", () => {
  it("picker rows use the handle and a kind hint", () => {
    const out = taggableHousehold([
      m({ id: "a", handle: "biscuit", species: "Dog" }),
      m({ id: "b", kind: "person", handle: "james", relation: "Son" }),
      m({ id: "c", handle: null }),
    ]);
    expect(out.map((x) => [x.id, x.username, x.hint])).toEqual([
      ["h:a", "biscuit", "Dog"],
      ["h:b", "james", "Son"],
    ]);
  });

  it("renders a pet handle as a chip to its page; people stay profile links", () => {
    renderWithProviders(
      <Markdown content="Walking @biscuit with @ruth" mentions />,
    );
    expect(screen.getByRole("link", { name: "Biscuit" })).toHaveAttribute(
      "href",
      "/app/household/h1",
    );
    expect(screen.getByRole("link", { name: "@ruth" })).toHaveAttribute(
      "href",
      "/app/u/ruth",
    );
  });
});
