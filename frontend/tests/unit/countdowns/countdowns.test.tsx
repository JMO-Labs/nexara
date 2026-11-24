/**
 * @file tests/unit/countdowns/countdowns.test.tsx
 * @brief CountdownCard day text, optimistic follow, composer payload.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const follow = vi.fn();
const unfollow = vi.fn();
const create = vi.fn();
vi.mock("@/lib/api/countdowns", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/countdowns")>()),
  followCountdown: (...a: unknown[]) => follow(...a),
  unfollowCountdown: (...a: unknown[]) => unfollow(...a),
  createCountdown: (...a: unknown[]) => create(...a),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [] }),
}));

import { CountdownCard } from "@/components/countdowns/CountdownCard";
import { CountdownComposer } from "@/components/countdowns/CountdownComposer";
import type { Countdown } from "@/lib/api/countdowns";

const base: Countdown = {
  id: "c1",
  author_id: "u1",
  title: "Trip",
  target_date: "2026-06-11",
  target_time: null,
  tz: "UTC",
  emoji: null,
  cover_media_id: null,
  repeat_yearly: false,
  visibility: "community",
  subgroup_id: null,
  post_id: null,
  days_left: 1,
  next_date: "2026-06-11",
  following: false,
  follower_count: 2,
};
const NOW = new Date(2026, 5, 10, 15, 0);

function wrap(ui: React.ReactElement, qc?: QueryClient) {
  const client =
    qc ?? new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("CountdownCard", () => {
  it("uses singular for 1 day", () => {
    wrap(<CountdownCard c={base} now={NOW} />);
    expect(screen.getByText("day until")).toBeInTheDocument();
  });

  it("shows Today! on day 0", () => {
    wrap(<CountdownCard c={{ ...base, next_date: "2026-06-10" }} now={NOW} />);
    expect(screen.getByText("Today!")).toBeInTheDocument();
  });

  it("follow toggles and updates count optimistically", async () => {
    const qc = new QueryClient();
    qc.setQueryData(["countdowns", "c1"], base);
    follow.mockReturnValue(new Promise(() => {}));
    wrap(<CountdownCard c={base} now={NOW} />, qc);
    await userEvent.click(screen.getByRole("button", { name: "Follow" }));
    await waitFor(() =>
      expect(qc.getQueryData<Countdown>(["countdowns", "c1"])).toMatchObject({
        following: true,
        follower_count: 3,
      }),
    );
    expect(follow).toHaveBeenCalledWith("c1");
  });
});

describe("CountdownComposer", () => {
  it("posts the payload", async () => {
    create.mockResolvedValue(base);
    const onClose = vi.fn();
    wrap(<CountdownComposer open onClose={onClose} />);
    await userEvent.type(screen.getByLabelText("Title"), "Trip");
    await userEvent.type(screen.getByLabelText("Date"), "2026-06-11");
    await userEvent.click(
      screen.getByRole("switch", { name: "Repeats every year" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create.mock.calls[0][0]).toMatchObject({
      title: "Trip",
      target_date: "2026-06-11",
      repeat_yearly: true,
      visibility: "community",
    });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });
});
