/**
 * @file tests/unit/home/HomeSideColumn.test.tsx
 * @brief Side column: rail opens on hover/focus/tap and closes after leave.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { act, screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/hooks/useHomePeople", () => ({
  useHomePeople: () => ({
    data: {
      items: [
        { user_id: "u1", display_name: "Ruth A", birthday_in_days: 2 },
        { user_id: "u2", display_name: "Leo S", favorite: true },
      ],
    },
  }),
}));
vi.mock("@/hooks/useCommunityId", () => ({ useCommunityId: () => "c1" }));
vi.mock("@/hooks/useLists", () => ({
  useLists: () => ({ data: { lists: [{ itemCount: 5, completedCount: 2 }] } }),
}));
vi.mock("@/hooks/useWeather", () => ({
  useTempUnit: () => ["F", vi.fn()],
  useWeatherBoard: () => ({
    data: [
      { kind: "self", label: "Mesa", forecast: { current: { temp_c: 22 } } },
    ],
  }),
}));
vi.mock("@/components/home/tiles/PeopleTile", () => ({
  PeopleTile: () => <section>people</section>,
}));
vi.mock("@/components/home/tiles/WeatherTile", () => ({
  WeatherTile: () => <section>weather</section>,
}));
vi.mock("@/components/home/tiles/ListsTile", () => ({
  ListsTile: () => <section>lists</section>,
}));

import { HomeSideColumn } from "@/components/home/HomeSideColumn";

const side = () => screen.getByTestId("home-side");

describe("HomeSideColumn", () => {
  afterEach(() => vi.useRealTimers());

  it("opens on mouse hover and closes shortly after leaving", () => {
    vi.useFakeTimers();
    renderWithProviders(<HomeSideColumn open={null} onToggle={vi.fn()} />);
    expect(side()).not.toHaveAttribute("data-expanded");
    fireEvent.pointerEnter(side(), { pointerType: "mouse" });
    expect(side()).toHaveAttribute("data-expanded");
    fireEvent.pointerLeave(side(), { pointerType: "mouse" });
    expect(side()).toHaveAttribute("data-expanded");
    act(() => vi.advanceTimersByTime(300));
    expect(side()).not.toHaveAttribute("data-expanded");
  });

  it("re-entering before the delay keeps it open", () => {
    vi.useFakeTimers();
    renderWithProviders(<HomeSideColumn open={null} onToggle={vi.fn()} />);
    fireEvent.pointerEnter(side(), { pointerType: "mouse" });
    fireEvent.pointerLeave(side(), { pointerType: "mouse" });
    act(() => vi.advanceTimersByTime(100));
    fireEvent.pointerEnter(side(), { pointerType: "mouse" });
    act(() => vi.advanceTimersByTime(500));
    expect(side()).toHaveAttribute("data-expanded");
  });

  it("tap toggles and shows birthday count", () => {
    renderWithProviders(<HomeSideColumn open={null} onToggle={vi.fn()} />);
    const people = screen.getByRole("button", {
      name: "People, 1 birthday soon",
    });
    fireEvent.click(people);
    expect(people).toHaveAttribute("aria-expanded", "true");
    fireEvent.keyDown(people, { key: "Escape" });
    expect(people).toHaveAttribute("aria-expanded", "false");
  });

  it("shows live glances in the pill", () => {
    renderWithProviders(<HomeSideColumn open={null} onToggle={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: "Weather, 72° Mesa" }),
    ).toHaveTextContent("72°");
    expect(
      screen.getByRole("button", { name: "Lists, 3 open items" }),
    ).toHaveTextContent("3");
  });
});
