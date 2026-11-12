/**
 * @file tests/unit/calendar/CalendarSubscriptions.test.tsx
 * @brief Export-as-iCal button and subscription row (last/next sync, actions).
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import en from "@/i18n/en-US.json";
import { ExportIcalButton } from "@/components/events/event-detail/ExportIcalButton";
import { SubscriptionRow } from "@/components/events/subscriptions/SubscriptionRow";
import type { CalendarSubscription } from "@/lib/api/events";

function wrap(ui: React.ReactElement) {
  return render(
    <NextIntlClientProvider locale="en" messages={en}>
      {ui}
    </NextIntlClientProvider>,
  );
}

describe("ExportIcalButton", () => {
  it("links to the event .ics endpoint as a download", () => {
    wrap(<ExportIcalButton eventId="ev 1" />);
    const link = screen.getByRole("link", { name: /export as ical/i });
    expect(link.getAttribute("href")).toBe("/api/v1/events/ev%201/ical");
    expect(link.hasAttribute("download")).toBe(true);
  });
});

describe("SubscriptionRow", () => {
  const sub: CalendarSubscription = {
    id: "s1",
    title: "Work",
    source_url: "https://example.com/c.ics",
    last_synced_at: new Date(Date.now() - 3600_000 * 2).toISOString(),
    next_sync_at: new Date(Date.now() + 3600_000 * 3).toISOString(),
    sync_error: null,
    sync_interval_minutes: 60,
  };

  it("shows last sync and next sync", () => {
    wrap(
      <SubscriptionRow
        sub={sub}
        onDelete={vi.fn()}
        onSync={vi.fn()}
        isSyncing={false}
      />,
    );
    expect(screen.getByText(/Last sync: .*2 hours ago/)).toBeTruthy();
    expect(screen.getByText(/Next sync: in .*3 hours/)).toBeTruthy();
  });

  it("calls onSync from the sync-now button", () => {
    const onSync = vi.fn();
    wrap(
      <SubscriptionRow
        sub={sub}
        onDelete={vi.fn()}
        onSync={onSync}
        isSyncing={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Sync Work now" }));
    expect(onSync).toHaveBeenCalledWith("s1");
  });

  it("calls onDelete after confirming", () => {
    const onDelete = vi.fn();
    wrap(
      <SubscriptionRow
        sub={sub}
        onDelete={onDelete}
        onSync={vi.fn()}
        isSyncing={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete Work" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledWith("s1");
  });
});
