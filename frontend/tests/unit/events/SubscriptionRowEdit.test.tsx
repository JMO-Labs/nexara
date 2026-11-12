/**
 * @file tests/unit/events/SubscriptionRowEdit.test.tsx
 * @brief Toggle, frequency and edit behaviour of calendar subscription rows,
 *        plus API path/field mapping to the backend.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SubscriptionRow } from "@/components/events/subscriptions/SubscriptionRow";
import { INTERVALS } from "@/components/events/subscriptions/intervals";
import * as client from "@/lib/api/client";
import { listSubscriptions, updateSubscription } from "@/lib/api/events";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof client>()),
  apiGet: vi.fn(),
  apiPut: vi.fn(),
}));

const sub = {
  id: "s1",
  title: "Work",
  source_url: "https://e.com/a.ics",
  last_synced_at: null,
  sync_error: null,
  sync_interval_minutes: 60,
  sync_enabled: true,
};

describe("SubscriptionRow", () => {
  const onUpdate = vi.fn();
  beforeEach(() => vi.clearAllMocks());
  const setup = () =>
    render(
      <SubscriptionRow
        sub={sub}
        onDelete={vi.fn()}
        onSync={vi.fn()}
        onUpdate={onUpdate}
        isSyncing={false}
      />,
    );

  it("offers hourly, daily and weekly only", () => {
    expect(INTERVALS.map((i) => i[0])).toEqual([60, 1440, 10080]);
  });

  it("toggles sync_enabled", () => {
    setup();
    fireEvent.click(screen.getByRole("switch"));
    expect(onUpdate).toHaveBeenCalledWith("s1", { sync_enabled: false });
  });

  it("saves edits from the edit modal", () => {
    setup();
    fireEvent.click(screen.getByLabelText("Edit Work"));
    fireEvent.change(screen.getByDisplayValue("Work"), {
      target: { value: "Job" },
    });
    fireEvent.click(screen.getByText("actions.save"));
    expect(onUpdate).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({ title: "Job" }),
    );
  });
});

describe("events api subscriptions", () => {
  beforeEach(() => vi.clearAllMocks());

  it("maps backend name to title", async () => {
    vi.mocked(client.apiGet).mockResolvedValue([
      { id: "a", name: "N", source_url: "u", sync_interval_minutes: 60 },
    ]);
    const r = await listSubscriptions();
    expect(client.apiGet).toHaveBeenCalledWith(
      "/api/v1/calendar-subscriptions",
    );
    expect(r[0].title).toBe("N");
  });

  it("PUTs title as name", async () => {
    vi.mocked(client.apiPut).mockResolvedValue({ id: "a", name: "N" });
    await updateSubscription("a", { title: "N", sync_enabled: false });
    expect(client.apiPut).toHaveBeenCalledWith(
      "/api/v1/calendar-subscriptions/a",
      { name: "N", sync_enabled: false },
    );
  });
});
