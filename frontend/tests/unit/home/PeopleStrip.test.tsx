/**
 * @file tests/unit/home/PeopleStrip.test.tsx
 * @brief PeopleStrip: status labels, ring, card actions, empty state.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

let items: unknown[] = [];
vi.mock("@/hooks/useHomePeople", () => ({
  useHomePeople: () => ({ data: { items } }),
}));

const mutateAsync = vi.fn();
vi.mock("@/hooks/useChat", () => ({
  useCreateDm: () => ({ mutateAsync }),
}));

import { PeopleStrip } from "@/components/home/PeopleStrip";

const person = (o: Record<string, unknown> = {}) => ({
  user_id: "u1",
  username: "tomas",
  display_name: "Tomás Reyes",
  avatar_url: null,
  online: false,
  birthday_in_days: null,
  last_seen_at: null,
  shared_groups: [{ id: "g1", name: "Family", accent_color: "#112233" }],
  primary_group_id: "g1",
  shared_events_30d: 3,
  ...o,
});

beforeEach(() => {
  items = [];
  push.mockReset();
  mutateAsync.mockReset();
});

describe("PeopleStrip", () => {
  it("renders nothing with zero people", () => {
    renderWithProviders(<PeopleStrip />);
    expect(screen.queryByLabelText("Your people")).toBeNull();
  });

  it("labels online person", () => {
    items = [person({ online: true })];
    renderWithProviders(<PeopleStrip />);
    expect(
      screen.getByRole("button", { name: "Tomás Reyes, Online now" }),
    ).toBeInTheDocument();
  });

  it("labels birthday today and in n days", () => {
    items = [
      person({ birthday_in_days: 0 }),
      person({ user_id: "u2", display_name: "Sam Lee", birthday_in_days: 3 }),
    ];
    renderWithProviders(<PeopleStrip />);
    expect(
      screen.getByRole("button", { name: "Tomás Reyes, Birthday today" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sam Lee, Birthday in 3 days" }),
    ).toBeInTheDocument();
  });

  it("labels last seen and applies group ring", () => {
    items = [
      person({
        last_seen_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
      }),
    ];
    renderWithProviders(<PeopleStrip />);
    const btn = screen.getByRole("button", {
      name: "Tomás Reyes, Active 3h ago",
    });
    expect(btn.style.getPropertyValue("--rc")).toBe("#112233");
  });

  it("card shows shared info and Message opens the DM", async () => {
    items = [person()];
    mutateAsync.mockResolvedValue({ id: "ch9" });
    renderWithProviders(<PeopleStrip />);
    expect(screen.getByText("Add how you know Tomás")).toBeInTheDocument();
    expect(screen.getByText("Family")).toBeInTheDocument();
    expect(screen.getByText("3 shared events this month")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Message" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/app/chat/ch9"));
    expect(mutateAsync).toHaveBeenCalledWith("u1");
    fireEvent.click(screen.getByRole("button", { name: "Profile" }));
    expect(push).toHaveBeenCalledWith("/app/members/u1");
  });

  it("omits shared events line when 0", () => {
    items = [person({ shared_events_30d: 0 })];
    renderWithProviders(<PeopleStrip />);
    expect(screen.queryByText(/shared events/)).toBeNull();
  });
});
