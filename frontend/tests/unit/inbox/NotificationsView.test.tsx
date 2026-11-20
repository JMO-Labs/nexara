/**
 * @file tests/unit/inbox/NotificationsView.test.tsx
 * @brief NotificationsView: filter toggle, list, mark all read.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";
import { markAllRead } from "@/lib/api/notifications";
import { NotificationsView } from "@/components/inbox/NotificationsView";

vi.mock("@/lib/api/notifications", () => ({
  markAllRead: vi.fn(),
}));
vi.mock("@/hooks/useNotificationsSync", () => ({
  useNotificationsSync: vi.fn(),
}));
vi.mock("@/components/notifications/NotificationList", () => ({
  NotificationList: (p: { filter: string }) => (
    <div data-testid="list">{p.filter}</div>
  ),
}));

function setup() {
  render(
    <NextIntlClientProvider locale="en-US" messages={messages}>
      <QueryClientProvider client={new QueryClient()}>
        <NotificationsView />
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

describe("NotificationsView", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the list with the All filter and no page heading", () => {
    setup();
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(screen.getByTestId("list")).toHaveTextContent("all");
  });

  it("switches the filter via Segmented", async () => {
    setup();
    await userEvent.click(screen.getByRole("radio", { name: "Unread" }));
    expect(screen.getByTestId("list")).toHaveTextContent("unread");
  });

  it("Mark all read calls the API", async () => {
    vi.mocked(markAllRead).mockResolvedValue({ message: "ok" });
    setup();
    await userEvent.click(
      screen.getByRole("button", { name: "Mark all as read" }),
    );
    await waitFor(() => expect(markAllRead).toHaveBeenCalled());
  });
});
