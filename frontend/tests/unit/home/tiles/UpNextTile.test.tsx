/**
 * @file tests/unit/home/tiles/UpNextTile.test.tsx
 * @brief UpNextTile: RSVP state, scope filter, empty state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../../utils/renderWithProviders";

const mutate = vi.fn();
let items: unknown[] = [];
vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: () => ({ data: { items } }),
  useRsvp: () => ({ mutate }),
}));

import { UpNextTile } from "@/components/home/tiles/UpNextTile";
import { useHomeScope } from "@/stores/homeScope";

const ev = (id: string, over: Record<string, unknown> = {}) => ({
  id,
  title: `Event ${id}`,
  starts_at: "2026-11-21T18:00:00Z",
  location: "Park",
  subgroup_id: null,
  user_rsvp: null,
  ...over,
});

const ui = () => <UpNextTile open onToggle={() => {}} />;

describe("UpNextTile", () => {
  beforeEach(() => {
    mutate.mockReset();
    useHomeScope.setState({ scope: "all" });
  });

  it("shows Going for attending and RSVP button otherwise", () => {
    items = [ev("a", { user_rsvp: { status: "attending" } }), ev("b")];
    renderWithProviders(ui());
    expect(screen.getByLabelText("Going")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^RSVP/ }));
    expect(mutate).toHaveBeenCalledWith("attending");
  });

  it("filters by scope and caps at 3", () => {
    items = [
      ev("a", { subgroup_id: "g1" }),
      ev("b", { subgroup_id: "g2" }),
      ev("c", { subgroup_id: "g1" }),
      ev("d", { subgroup_id: "g1" }),
      ev("e", { subgroup_id: "g1" }),
    ];
    useHomeScope.setState({ scope: "g1" });
    renderWithProviders(ui());
    expect(screen.queryByText("Event b")).toBeNull();
    expect(screen.getByText("Event a")).toBeInTheDocument();
    expect(screen.getByText("Event d")).toBeInTheDocument();
    expect(screen.queryByText("Event e")).toBeNull();
  });

  it("shows an empty state", () => {
    items = [];
    renderWithProviders(ui());
    expect(screen.getByText("Nothing coming up")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Plan an event" })).toHaveAttribute(
      "href",
      "/app/events",
    );
  });

  it("links an event to its page", () => {
    items = [ev("a")];
    renderWithProviders(ui());
    expect(screen.getByRole("link", { name: /Event a/ })).toHaveAttribute(
      "href",
      "/app/events/a",
    );
  });
});
