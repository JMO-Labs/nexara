/**
 * @file tests/unit/components/trips/trips.test.tsx
 * @brief Active trip bar, watching chips and the start dialog validation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  startTrip: vi.fn(),
  getActiveTrip: vi.fn(),
  listWatching: vi.fn(),
  arriveTrip: vi.fn(),
  extendTrip: vi.fn(),
  cancelTrip: vi.fn(),
}));
vi.mock("@/lib/api/trips", () => api);
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => true }));
vi.mock("@/hooks/useMembersList", () => ({
  useMembersList: () => ({
    data: [{ id: "u2", display_name: "Maya", username: "maya" }],
  }),
}));

import { ActiveTripBar } from "@/components/trips/ActiveTripBar";
import { WatchingChips } from "@/components/trips/WatchingChips";
import { StartTripDialog } from "@/components/trips/StartTripDialog";

const trip = {
  id: "t1",
  label: "Grandma's",
  expected_at: new Date(Date.now() + 3_600_000).toISOString(),
  arrived_at: null,
  alerted_at: null,
  ended_at: null,
  traveler: { id: "u1", display_name: "Ruth Lee" },
  watchers: [],
};

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => vi.clearAllMocks());

describe("trips ui", () => {
  it("bar shows nothing without a trip", () => {
    api.getActiveTrip.mockResolvedValue(null);
    wrap(<ActiveTripBar />);
    expect(screen.queryByLabelText("Active trip")).toBeNull();
  });

  it("Made it arrives the active trip", async () => {
    api.getActiveTrip.mockResolvedValue(trip);
    api.arriveTrip.mockResolvedValue({ ...trip, arrived_at: "x" });
    wrap(<ActiveTripBar />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Made it" }),
    );
    expect(api.arriveTrip).toHaveBeenCalledWith("t1");
  });

  it("chips list watched travelers", async () => {
    api.listWatching.mockResolvedValue([trip]);
    wrap(<WatchingChips />);
    expect(await screen.findByText(/Ruth to Grandma's/)).toBeTruthy();
  });

  it("start dialog blocks without watchers or valid time", async () => {
    wrap(<StartTripDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText("Where are you going?"), "Home");
    await userEvent.click(screen.getByRole("button", { name: "Start trip" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(
      /arrival time/,
    );
    expect(api.startTrip).not.toHaveBeenCalled();
  });
});
