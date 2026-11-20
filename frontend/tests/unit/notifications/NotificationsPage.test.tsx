/**
 * @file tests/unit/notifications/NotificationsPage.test.tsx
 * @brief /app/notifications: header, filter toggle, mark all read.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";
import { markAllRead } from "@/lib/api/notifications";
import NotificationsPage from "@/app/app/notifications/page";

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
        <NotificationsPage />
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

describe("NotificationsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders title and list with the All filter", () => {
    setup();
    expect(
      screen.getByRole("heading", { level: 1, name: "Notifications" }),
    ).toBeInTheDocument();
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
