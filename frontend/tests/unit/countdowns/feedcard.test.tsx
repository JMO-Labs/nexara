/**
 * @file tests/unit/countdowns/feedcard.test.tsx
 * @brief CountdownFeedCard loading and unavailable states.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const state = { data: undefined as unknown, isError: false };
vi.mock("@/hooks/useCountdowns", () => ({ useCountdown: () => state }));
import { CountdownFeedCard } from "@/components/countdowns/CountdownFeedCard";

const r = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <CountdownFeedCard id="x" />
    </QueryClientProvider>,
  );

describe("CountdownFeedCard", () => {
  it("shows skeleton while loading", () => {
    r();
    expect(screen.getByTestId("countdown-loading")).toBeInTheDocument();
  });
  it("shows placeholder on error", () => {
    state.isError = true;
    r();
    expect(screen.getByText("Countdown unavailable")).toBeInTheDocument();
  });
});
