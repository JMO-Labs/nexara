/**
 * @file tests/unit/newsletter/NewsletterView.test.tsx
 * @brief Newsletter sheet: sections, print button, admin bar gating, API paths.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../utils/renderWithProviders";

const apiGet = vi.fn().mockResolvedValue({});
const apiPut = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiGet: (...a: unknown[]) => apiGet(...a),
  apiPut: (...a: unknown[]) => apiPut(...a),
}));

import {
  NewsletterView,
  shiftMonth,
} from "@/components/newsletter/NewsletterView";
import { getNewsletter, setNewsletterOverride } from "@/lib/api/newsletter";
import type { Newsletter } from "@/lib/api/newsletter";

const data: Newsletter = {
  month: "2026-11",
  community_name: "Soto family",
  top_posts: [
    {
      id: "p1",
      author_name: "Ruth",
      excerpt: "Thanksgiving was lovely",
      created_at: "2026-11-26T10:00:00Z",
      reactions: 4,
      comments: 2,
      pinned: false,
      media_ids: ["m1"],
    },
  ],
  photos: [{ media_id: "m1", post_id: "p1", alt: null }],
  birthdays: [{ name: "Maya", date: "2026-11-09", link: "/app/u/maya" }],
  remembrances: [],
  new_recipes: [{ id: "r1", title: "Pie", author_name: "Ruth" }],
  opened_capsules: [],
  events: [{ id: "e1", title: "Picnic", date: "2026-11-14", place: "Park" }],
  hidden_posts: [
    {
      id: "p2",
      author_name: "Sam",
      excerpt: "Hidden one",
      created_at: "2026-11-02T10:00:00Z",
      reactions: 0,
      comments: 0,
      pinned: false,
      media_ids: [],
    },
  ],
};

describe("NewsletterView", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders masthead and sections", () => {
    renderWithProviders(
      <NewsletterView data={data} admin={false} canPrev canNext={false} />,
    );
    expect(
      screen.getByRole("heading", { level: 1, name: /Soto family news/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("November 2026")).toBeInTheDocument();
    expect(screen.getByText("Thanksgiving was lovely")).toBeInTheDocument();
    expect(screen.getByText(/Park/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Curate this newsletter")).toBeNull();
    expect(screen.queryByRole("link", { name: "Next month" })).toBeNull();
    expect(
      screen.getByRole("link", { name: "Previous month" }),
    ).toHaveAttribute("href", "/app/newsletter/2026-10");
  });

  it("prints on click", async () => {
    const print = vi.spyOn(window, "print").mockImplementation(() => {});
    renderWithProviders(
      <NewsletterView data={data} admin={false} canPrev canNext />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Print or save as PDF/ }),
    );
    expect(print).toHaveBeenCalled();
  });

  it("admin bar pins, hides and restores", async () => {
    renderWithProviders(<NewsletterView data={data} admin canPrev canNext />);
    await userEvent.click(screen.getByLabelText("Pin post by Ruth"));
    expect(apiPut).toHaveBeenCalledWith(
      "/api/v1/admin/newsletter/2026-11/overrides",
      { post_id: "p1", action: "pin" },
    );
    await userEvent.click(screen.getByLabelText("Restore post by Sam"));
    expect(apiPut).toHaveBeenLastCalledWith(
      "/api/v1/admin/newsletter/2026-11/overrides",
      { post_id: "p2", action: null },
    );
  });
});

describe("newsletter api + helpers", () => {
  it("uses /api/v1 paths", async () => {
    await getNewsletter("2026-11");
    expect(apiGet).toHaveBeenCalledWith("/api/v1/newsletter/2026-11");
    await setNewsletterOverride("2026-11", "p", "hide");
    expect(apiPut.mock.calls[0][0]).toBe(
      "/api/v1/admin/newsletter/2026-11/overrides",
    );
  });
  it("shiftMonth crosses years", () => {
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
  });
});
