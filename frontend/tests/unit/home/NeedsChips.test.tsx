/**
 * @file tests/unit/home/NeedsChips.test.tsx
 * @brief NeedsChips: chip kinds, links, truncation, empty state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

let needs: unknown = undefined;
vi.mock("@/hooks/useHomeNeeds", () => ({
  useHomeNeeds: () => ({ data: needs }),
}));

import { NeedsChips } from "@/components/home/NeedsChips";

beforeEach(() => {
  needs = undefined;
});

describe("NeedsChips", () => {
  it("renders all four chip kinds with links", () => {
    needs = {
      rsvps: [{ event_id: "e1", title: "Thanksgiving", starts_at: "x" }],
      polls: [{ post_id: "p1", question: "Carpool" }],
      prompt: { prompt_post_id: "pp", post_id: "p2", title: "T" },
      list_items: { count: 2, list_id: "l1", list_title: "Groceries" },
    };
    renderWithProviders(<NeedsChips />);
    expect(screen.getByText("Needs you")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /RSVP to Thanksgiving/ }),
    ).toHaveAttribute("href", "/app/events?event=e1");
    expect(screen.getByRole("link", { name: /Vote: Carpool/ })).toHaveAttribute(
      "href",
      "/app/post/p1",
    );
    expect(
      screen.getByRole("link", { name: /Today's prompt/ }),
    ).toHaveAttribute("href", "/app/prompts/pp");
    expect(
      screen.getByRole("link", { name: /2 list items due/ }),
    ).toHaveAttribute("href", "/app/lists/l1");
  });

  it("renders nothing when empty", () => {
    needs = { rsvps: [], polls: [], prompt: null, list_items: null };
    renderWithProviders(<NeedsChips />);
    expect(screen.queryByLabelText("Needs you")).toBeNull();
  });

  it("renders nothing while loading", () => {
    renderWithProviders(<NeedsChips />);
    expect(screen.queryByLabelText("Needs you")).toBeNull();
  });

  it("truncates long chip text at 28 chars", () => {
    needs = {
      rsvps: [
        {
          event_id: "e1",
          title: "A very long event title that keeps going",
          starts_at: "x",
        },
      ],
      polls: [],
      prompt: null,
      list_items: null,
    };
    renderWithProviders(<NeedsChips />);
    const full = "RSVP to A very long event title that keeps going";
    const text = full.slice(0, 28) + "…";
    expect(screen.getByText(text)).toBeInTheDocument();
  });
});

describe("NeedsChips quick nav", () => {
  it("shows N unanswered button, hides at 0", async () => {
    const { useQotd } = await import("@/stores/qotd");
    needs = {
      rsvps: [],
      polls: [],
      prompt: { prompt_post_id: "pp", post_id: "p2", title: "T" },
      list_items: null,
    };
    useQotd.setState({ ids: ["a", "b"], answered: { a: false, b: false } });
    const { unmount } = renderWithProviders(<NeedsChips />);
    expect(
      screen.getByRole("button", { name: "2 unanswered" }),
    ).toBeInTheDocument();
    unmount();
    useQotd.setState({ answered: { a: true, b: true } });
    renderWithProviders(<NeedsChips />);
    expect(screen.queryByText("Needs you")).toBeNull();
    useQotd.setState({ ids: null, answered: {} });
  });
});
