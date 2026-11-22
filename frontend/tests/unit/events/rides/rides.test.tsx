/**
 * @file tests/unit/events/rides/rides.test.tsx
 * @brief Rides API paths, RideCard actions, RidesSection feature gate.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const client = vi.hoisted(() => ({
  apiGet: vi.fn().mockResolvedValue([]),
  apiPost: vi.fn().mockResolvedValue({}),
  apiDelete: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  ...client,
}));
let featureOn = true;
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => featureOn }));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: any) => unknown) => sel({ user: { id: "me" } }),
}));

import * as api from "@/lib/api/rides";
import { RideCard } from "@/components/events/rides/RideCard";
import { RidesSection } from "@/components/events/rides/RidesSection";

const ride = (o: Partial<api.Ride> = {}): api.Ride => ({
  id: "r1",
  event_id: "e1",
  kind: "offer",
  user_id: "dee",
  driver_name: "Dee",
  seats: 3,
  seats_left: 2,
  origin: "Elm St",
  depart_at: "2026-12-01T15:00:00Z",
  note: "",
  passengers: [],
  joined: false,
  created_at: "2026-11-01T00:00:00Z",
  ...o,
});

beforeEach(() => {
  vi.clearAllMocks();
  featureOn = true;
});

describe("rides api", () => {
  it("uses /api/v1/ paths", async () => {
    const b = { seats: 1, origin: "", depart_at: null, note: "" };
    await api.listRides("e1");
    await api.offerRide("e1", b);
    await api.requestRide("e1", b);
    await api.joinRide("r1", 2);
    await api.leaveRide("r1");
    await api.answerRequest("q1", "r1");
    await api.cancelRide("r1");
    const paths = [
      ...client.apiGet.mock.calls,
      ...client.apiPost.mock.calls,
      ...client.apiDelete.mock.calls,
    ].map((c) => c[0] as string);
    expect(client.apiPost).toHaveBeenCalledWith("/api/v1/rides/r1/join", {
      seats: 2,
    });
    expect(paths).toEqual([
      "/api/v1/events/e1/rides",
      "/api/v1/events/e1/rides/offers",
      "/api/v1/events/e1/rides/requests",
      "/api/v1/rides/r1/join",
      "/api/v1/rides/r1/leave",
      "/api/v1/rides/q1/answer",
      "/api/v1/rides/r1",
    ]);
    expect(paths.every((p) => p.startsWith("/api/v1/"))).toBe(true);
  });
});

describe("RideCard", () => {
  const h = () => ({
    onJoin: vi.fn(),
    onLeave: vi.fn(),
    onCancel: vi.fn(),
    onAnswer: vi.fn(),
  });
  it("offer: shows seats left and joins", () => {
    const p = h();
    render(
      <RideCard
        ride={ride()}
        userId="me"
        myOpenOffers={[]}
        busy={false}
        {...p}
      />,
    );
    expect(screen.getByText("2 of 3 seats left")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Join ride" }));
    expect(p.onJoin).toHaveBeenCalledWith("r1", 1);
  });
  it("full offer disables join", () => {
    render(
      <RideCard
        ride={ride({ seats_left: 0 })}
        userId="me"
        myOpenOffers={[]}
        busy={false}
        {...h()}
      />,
    );
    expect(
      (screen.getByRole("button", { name: "Full" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
  it("request: driver can take them", () => {
    const p = h();
    render(
      <RideCard
        ride={ride({
          kind: "request",
          user_id: "maya",
          driver_name: "Maya",
          seats: 1,
        })}
        userId="me"
        myOpenOffers={[ride({ id: "mine", user_id: "me" })]}
        busy={false}
        {...p}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /I can take Maya/ }));
    expect(p.onAnswer).toHaveBeenCalledWith("r1", "mine");
  });
  it("own ride can be cancelled", () => {
    const p = h();
    render(
      <RideCard
        ride={ride({ user_id: "me" })}
        userId="me"
        myOpenOffers={[]}
        busy={false}
        {...p}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel offer" }));
    expect(p.onCancel).toHaveBeenCalledWith("r1");
  });
});

describe("RideCard seats", () => {
  it("picker is bounded by seats left and passes the choice", () => {
    const onJoin = vi.fn();
    render(
      <RideCard
        ride={ride({
          seats_left: 2,
          passengers: [{ user_id: "x", display_name: "Ruth", seats: 3 }],
        })}
        userId="me"
        myOpenOffers={[]}
        busy={false}
        onJoin={onJoin}
        onLeave={vi.fn()}
        onCancel={vi.fn()}
        onAnswer={vi.fn()}
      />,
    );
    expect(screen.getByText("Riding: Ruth (3 seats)")).toBeTruthy();
    const sel = screen.getByLabelText("Seats") as HTMLSelectElement;
    expect(sel.options.length).toBe(2);
    fireEvent.change(sel, { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Join ride" }));
    expect(onJoin).toHaveBeenCalledWith("r1", 2);
  });
});

describe("RidesSection", () => {
  const wrap = (ui: React.ReactElement) => (
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
  );
  it("renders nothing when feature is off", () => {
    featureOn = false;
    const { container } = render(wrap(<RidesSection eventId="e1" />));
    expect(container.innerHTML).toBe("");
    expect(client.apiGet).not.toHaveBeenCalled();
  });
  it("shows offer and request buttons when on", () => {
    render(wrap(<RidesSection eventId="e1" />));
    expect(screen.getByRole("button", { name: "Offer a ride" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Need a ride" })).toBeTruthy();
  });
});
