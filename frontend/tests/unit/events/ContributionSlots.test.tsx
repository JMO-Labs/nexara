/**
 * @file tests/unit/events/ContributionSlots.test.tsx
 * @brief Claim/unclaim buttons in the contribution slot list.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

const claim = vi.fn();
const unclaim = vi.fn();
let claimPending = false;

vi.mock("@/hooks/useEvents", () => ({
  useClaimContribution: () => ({ mutate: claim, isPending: claimPending }),
  useUnclaimContribution: () => ({ mutate: unclaim, isPending: false }),
}));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: any) => unknown) => sel({ user: { id: "me" } }),
}));

import { ContributionSlots } from "@/components/events/event-detail/ContributionSlots";

const slots = [
  {
    id: "s1",
    title: "Salad",
    quantity_needed: 2,
    quantity_claimed: 0,
    claimed_by: [],
  },
  {
    id: "s2",
    title: "Drinks",
    quantity_needed: 2,
    quantity_claimed: 1,
    claimed_by: ["me"],
  },
  {
    id: "s3",
    title: "Cake",
    quantity_needed: 1,
    quantity_claimed: 1,
    claimed_by: ["other"],
  },
];

describe("ContributionSlots", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    claimPending = false;
  });

  it("claims an open slot", () => {
    render(<ContributionSlots eventId="e1" slots={slots} />);
    fireEvent.click(screen.getByRole("button", { name: "Claim Salad" }));
    expect(claim).toHaveBeenCalledWith("s1");
  });

  it("unclaims own slot", () => {
    render(<ContributionSlots eventId="e1" slots={slots} />);
    fireEvent.click(screen.getByRole("button", { name: "Unclaim Drinks" }));
    expect(unclaim).toHaveBeenCalledWith("s2");
    expect(screen.queryByRole("button", { name: "Claim Drinks" })).toBeNull();
  });

  it("shows no button for a full slot claimed by others", () => {
    render(<ContributionSlots eventId="e1" slots={slots} />);
    expect(screen.queryByRole("button", { name: /Cake/ })).toBeNull();
  });

  it("disables buttons while pending", () => {
    claimPending = true;
    render(<ContributionSlots eventId="e1" slots={slots} />);
    expect(screen.getByRole("button", { name: "Claim Salad" })).toBeDisabled();
  });
});
