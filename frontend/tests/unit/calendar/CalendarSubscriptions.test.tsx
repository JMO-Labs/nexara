/**
 * @file tests/unit/calendar/CalendarSubscriptions.test.tsx
 * @brief Export-as-iCal button and subscription row (last/next sync, actions).
 */
import * as React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import en from "@/i18n/en-US.json";
import { ExportIcalButton } from "@/components/events/event-detail/ExportIcalButton";
import { SubscriptionRow } from "@/components/events/subscriptions/SubscriptionRow";
import type { CalendarSubscription } from "@/lib/api/events";
import { API_BASE, setAccessToken } from "@/lib/auth/session";

function wrap(ui: React.ReactElement) {
  return render(
    <NextIntlClientProvider locale="en" messages={en}>
      {ui}
    </NextIntlClientProvider>,
  );
}

describe("ExportIcalButton", () => {
  const { createObjectURL, revokeObjectURL } = URL;
  afterEach(() => {
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;
    setAccessToken(null);
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("fetches the .ics with the bearer token and downloads it", async () => {
    setAccessToken("tok-123");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n", {
        status: 200,
        headers: { "content-type": "text/calendar" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const createUrl = vi.fn().mockReturnValue("blob:ics");
    const revokeUrl = vi.fn();
    URL.createObjectURL = createUrl;
    URL.revokeObjectURL = revokeUrl;
    const clicked: { download: string; href: string | null }[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      function (this: HTMLAnchorElement) {
        const href = this.getAttribute("href");
        clicked.push({ download: this.download, href });
      },
    );

    wrap(<ExportIcalButton eventId="ev 1" title="Team BBQ" />);
    fireEvent.click(screen.getByRole("button", { name: /export as ical/i }));

    await waitFor(() => expect(clicked).toHaveLength(1));
    expect(clicked[0]).toEqual({ download: "Team BBQ.ics", href: "blob:ics" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE}/api/v1/events/ev%201/ical`);
    expect(new Headers(init.headers).get("Authorization")).toBe(
      "Bearer tok-123",
    );
    expect(createUrl.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect(revokeUrl).toHaveBeenCalledWith("blob:ics");
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
