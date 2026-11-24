/**
 * @file tests/unit/app/home-page.test.tsx
 * @brief Home page frame: greeting, scope bar, six slots, default accordion.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
vi.mock("@/components/home/CompleteProfileCard", () => ({
  CompleteProfileCard: () => null,
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/app",
}));
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

const chats = vi.hoisted(() => ({ data: { items: [] as unknown[] } }));

vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ user: { id: "u1", display_name: "Alice Smith" } }),
}));
vi.mock("@/hooks/useHomeChats", () => ({ useHomeChats: () => chats }));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [] }),
}));
vi.mock("@/components/home/tiles/FeedTile", () => ({
  FeedTile: ({
    open,
    onToggle,
  }: {
    open: boolean;
    onToggle: (id: "feed") => void;
  }) => (
    <button
      data-testid="feed"
      data-open={open}
      onClick={() => onToggle("feed")}
    />
  ),
}));
vi.mock("@/components/home/tiles/ChatsTile", () => ({
  ChatsTile: ({ open }: { open: boolean }) => (
    <div data-testid="chats" data-open={open} />
  ),
}));
vi.mock("@/components/home/tiles/UpNextTile", () => ({
  UpNextTile: ({ open }: { open: boolean }) => (
    <div data-testid="next" data-open={open} />
  ),
}));
vi.mock("@/components/home/tiles/PhotosTile", () => ({
  PhotosTile: ({ open }: { open: boolean }) => (
    <div data-testid="photos" data-open={open} />
  ),
}));
vi.mock("@/components/home/PeopleStrip", () => ({
  PeopleStrip: () => <div data-testid="people" />,
}));
vi.mock("@/components/home/NeedsChips", () => ({
  NeedsChips: () => <div data-testid="needs" />,
}));

import AppHome from "@/app/app/page";

beforeEach(() => {
  chats.data = { items: [] };
});

describe("AppHome page", () => {
  it("greets and renders the six slots without a nested main", () => {
    const { container } = renderWithProviders(<AppHome />);
    expect(
      screen.getByRole("heading", { level: 1, name: /^Good \w+, Alice$/ }),
    ).toBeInTheDocument();
    for (const id of ["feed", "chats", "next", "photos", "people", "needs"]) {
      expect(screen.getByTestId(id)).toBeInTheDocument();
    }
    expect(screen.getByRole("button", { name: /Everything/ })).toBeTruthy();
    expect(container.querySelector("main")).toBeNull();
  });

  it("opens Up next by default with no mentions", () => {
    renderWithProviders(<AppHome />);
    expect(screen.getByTestId("next").dataset.open).toBe("true");
    expect(screen.getByTestId("chats").dataset.open).toBe("false");
  });

  it("opens Chats by default when a thread mentions me", () => {
    chats.data = { items: [{ channel_id: "c1", mentions_me: true }] };
    renderWithProviders(<AppHome />);
    expect(screen.getByTestId("chats").dataset.open).toBe("true");
    expect(screen.getByTestId("next").dataset.open).toBe("false");
  });

  it("toggling a tile opens it and closes others", () => {
    renderWithProviders(<AppHome />);
    fireEvent.click(screen.getByTestId("feed"));
    expect(screen.getByTestId("feed").dataset.open).toBe("true");
    expect(screen.getByTestId("next").dataset.open).toBe("false");
  });
});
