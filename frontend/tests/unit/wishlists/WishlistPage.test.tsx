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
vi.mock("@/hooks/useMembers", () => ({
  useMemberProfile: () => ({ data: { display_name: "Ruth Alvarez" } }),
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
  occasion_date: "2026-12-12",
  note: null,
  visibility: "community",
  household: { id: "h1", name: "Biscuit", kind: "pet" },
  item_count: 3,
  is_owner: isOwner,
  items: [
    {
      id: "a",
      name: "Squeaky duck",
      url: null,
      price: "$8",
      notes: null,
      qty: 2,
      claimed: isOwner ? null : 1,
      mine: isOwner ? null : 0,
    },
    {
      id: "b",
      name: "Orthopedic bed",
      url: "https://example.com/bed",
      price: null,
      notes: null,
      qty: 1,
      claimed: isOwner ? null : 1,
      mine: isOwner ? null : 0,
    },
    {
      id: "c",
      name: "Bandana",
      url: null,
      price: null,
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
  });

  it("gift-giver sees what is left and can claim or undo", () => {
    list = base(false);
    renderWithProviders(<WishlistPage id="w1" />);
    expect(screen.getByText("1 of 2 left")).toBeInTheDocument();
    expect(screen.getByText("Someone has this")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "I'll get this" }));
    expect(claim).toHaveBeenCalledWith({ id: "w1", itemId: "a", qty: 1 });
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(release).toHaveBeenCalledWith({ id: "w1", itemId: "c" });
    expect(screen.queryByRole("form", { name: "Add a wish" })).toBeNull();
    expect(
      screen.getByRole("link", { name: /Orthopedic bed/ }),
    ).toHaveAttribute("href", "https://example.com/bed");
  });
});
