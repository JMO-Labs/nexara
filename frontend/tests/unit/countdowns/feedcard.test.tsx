/**
 * @file tests/unit/countdowns/feedcard.test.tsx
 * @brief CountdownFeedCard loading and unavailable states.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const state = { data: undefined as unknown, isError: false };
vi.mock("@/hooks/useCountdowns", () => ({ useCountdown: () => state }));
vi.mock("@/components/countdowns/FollowButton", () => ({
  FollowButton: () => null,
}));
import { CountdownFeedCard } from "@/components/countdowns/CountdownFeedCard";

const r = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <CountdownFeedCard id="x" authorName="Sam" />
    </QueryClientProvider>,
  );

describe("CountdownFeedCard", () => {
  it("shows skeleton while loading", () => {
    r();
    expect(screen.getByTestId("countdown-loading")).toBeInTheDocument();
  });
  it("shows the author line with the card", () => {
    state.data = {
      id: "x",
      title: "T",
      days_left: 3,
      next_date: "2030-01-01",
      follower_count: 0,
      following: false,
      repeat_yearly: false,
    };
    r();
    expect(screen.getByText("Sam started a countdown")).toBeInTheDocument();
    state.data = undefined;
  });
  it("shows placeholder on error", () => {
    state.isError = true;
    r();
    expect(screen.getByText("Countdown unavailable")).toBeInTheDocument();
  });
});
