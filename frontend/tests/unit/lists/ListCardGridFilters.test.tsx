/**
 * @file tests/unit/lists/ListCardGridFilters.test.tsx
 * @brief ListCardGrid visibility filter and sort order.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { list } from "./listFixtures";

const lists = [
  { ...list, id: "a", title: "Beta", visibility: "community", updatedAt: "2026-01-01T00:00:00Z", createdAt: "2026-03-01T00:00:00Z" },
  { ...list, id: "b", title: "Alpha", visibility: "private", updatedAt: "2026-02-01T00:00:00Z", createdAt: "2026-01-01T00:00:00Z" },
  { ...list, id: "c", title: "Gamma", visibility: "community", updatedAt: "2026-03-01T00:00:00Z", createdAt: "2026-02-01T00:00:00Z" },
];
vi.mock("@/hooks/useLists", () => ({
  useLists: () => ({ data: { lists }, isLoading: false }),
}));
vi.mock("@/components/lists/ListCard", () => ({
  ListCard: ({ list: l }: { list: { title: string } }) => <p>{l.title}</p>,
}));

import { ListCardGrid } from "@/components/lists/ListCardGrid";

const titles = () => screen.getAllByText(/Alpha|Beta|Gamma/).map((e) => e.textContent);

describe("ListCardGrid filters", () => {
  it("defaults to most recently updated first", () => {
    render(<ListCardGrid communityId="c1" />);
    expect(titles()).toEqual(["Gamma", "Alpha", "Beta"]);
  });
  it("filters by visibility and sorts by title", () => {
    render(<ListCardGrid communityId="c1" visibility="community" sortBy="title" />);
    expect(titles()).toEqual(["Beta", "Gamma"]);
  });
  it("sorts by created date", () => {
    render(<ListCardGrid communityId="c1" sortBy="created" />);
    expect(titles()).toEqual(["Beta", "Gamma", "Alpha"]);
  });
  it("shows an empty state when the filter matches nothing", () => {
    render(<ListCardGrid communityId="c1" visibility="subgroup" />);
    expect(screen.getByText("No lists yet")).toBeInTheDocument();
  });
});
