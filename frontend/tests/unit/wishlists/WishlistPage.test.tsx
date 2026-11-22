/**
 * @file tests/unit/wishlists/WishlistPage.test.tsx
 * @brief Owner view hides claims; gift-givers see what is left and can claim.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import type { WishlistDetail } from "@/lib/api/wishlists";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
const claim = vi.fn();
const release = vi.fn();
let list: WishlistDetail;
vi.mock("@/hooks/useWishlists", () => ({
  useWishlist: () => ({ data: list, isLoading: false, isError: false }),
  useWishlistActions: () => {
    const m = { mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false };
    return {
      addWish: m,
      updateWish: m,
      deleteWish: m,
      remove: m,
      update: m,
      create: m,
      claim: { ...m, mutate: claim },
      release: { ...m, mutate: release },
    };
  },
}));

import { WishlistPage } from "@/components/wishlists/WishlistPage";

const base = (isOwner: boolean): WishlistDetail => ({
  id: "w1",
  owner_id: "u1",
  title: "Biscuit turns 5",
  occasion: "birthday",
  owner_name: "Ruth Alvarez",
  occasion_label: null,
  event_date: "2026-12-12",
  due_by: null,
  note: null,
  visibility: "community",
  currency: "USD",
  budget_min_cents: null,
  budget_max_cents: null,
  event_budget_cents: null,
  giver_cap_cents: null,
  hide_claims: true,
  registry_links: [
    { label: "Amazon registry", url: "https://www.amazon.com/registry/x" },
  ],
  recipients: [
    { kind: "household", ref_id: "h1", name: "Biscuit", extra: "pet" },
  ],
  item_count: 3,
  is_owner: isOwner,
  can_edit_items: isOwner,
  sees_claims: !isOwner,
  planned_cents: isOwner ? 2400 : null,
  my_total_cents: isOwner ? 0 : 800,
  ship_to: {
    user_id: null,
    event_id: null,
    starts_at: null,
    name: null,
    address: "1 Elm St\nSpringfield",
  },
  items: [
    {
      id: "a",
      kind: "gift",
      price_auto: false,
      goal_cents: null,
      claimers: null,
      preview: null,
      name: "Squeaky duck",
      url: null,
      price_cents: 800,
      notes: null,
      qty: 2,
      claimed: isOwner ? null : 1,
      mine: isOwner ? null : 0,
    },
    {
      id: "b",
      kind: "gift",
      price_auto: true,
      goal_cents: null,
      claimers: null,
      preview: {
        id: "p1",
        title: "Orthopedic bed",
        site_name: "Amazon",
        has_image: false,
        price_cents: 5999,
        currency: "USD",
        buy_url: "https://www.amazon.com/dp/B07FZ8S74R?tag=nx-20",
        checked_at: new Date().toISOString(),
      },
      name: "Orthopedic bed",
      url: "https://www.amazon.com/dp/B07FZ8S74R",
      price_cents: 5999,
      notes: null,
      qty: 1,
      claimed: isOwner ? null : 1,
      mine: isOwner ? null : 0,
    },
    {
      id: "c",
      kind: "gift",
      price_auto: false,
      goal_cents: null,
      claimers: null,
      preview: null,
      name: "Bandana",
      url: null,
      price_cents: null,
      notes: null,
      qty: 1,
      claimed: isOwner ? null : 1,
      mine: isOwner ? null : 1,
    },
  ],
});

describe("WishlistPage", () => {
  beforeEach(() => {
    claim.mockReset();
    release.mockReset();
  });

  it("owner sees edit tools and no claim state", () => {
    list = base(true);
    renderWithProviders(<WishlistPage id="w1" />);
    expect(
      screen.getByRole("button", { name: "Edit Squeaky duck" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("form", { name: "Add a wish" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/I'll get this|Someone has this|You're getting/),
    ).toBeNull();
    expect(screen.getByText("× 2")).toBeInTheDocument();
    expect(
      screen.getByText(/won't see who is getting what/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Amazon registry/ }),
    ).toHaveAttribute("href", "https://www.amazon.com/registry/x");
    expect(screen.getByText(/1 Elm St/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy shipping address" }),
    ).toBeInTheDocument();
  });

  it("gift-giver sees what is left and can claim or undo", () => {
    list = base(false);
    renderWithProviders(<WishlistPage id="w1" />);
    expect(screen.getByText("1 of 2 left")).toBeInTheDocument();
    expect(screen.getByText("Someone has this")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "I'll get this" }));
    expect(claim.mock.calls[0][0]).toEqual({ id: "w1", itemId: "a", qty: 1 });
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(release).toHaveBeenCalledWith({ id: "w1", itemId: "c" });
    expect(screen.queryByRole("form", { name: "Add a wish" })).toBeNull();
    expect(
      screen.getByRole("link", { name: /Orthopedic bed/ }),
    ).toHaveAttribute("href", "https://www.amazon.com/dp/B07FZ8S74R?tag=nx-20");
    expect(
      screen.getByRole("button", {
        name: /Price from Amazon, checked .* It may differ for you/,
      }),
    ).toBeInTheDocument();
  });
});
