/**
 * @file tests/unit/settings/AppriseSection.test.tsx
 * @brief AppriseSection: add payload, blocked-URL message, matrix gating.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import en from "@/i18n/en-US.json";
import { ApiError } from "@/lib/api/errors";
import { NotificationMatrix } from "@/components/settings/NotificationMatrix";

vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) =>
    (en.settings.notif as Record<string, string>)[k] ?? k,
}));
const api = vi.hoisted(() => ({
  listAppriseUrls: vi.fn(),
  createAppriseUrl: vi.fn(),
  deleteAppriseUrl: vi.fn(),
  testAppriseUrl: vi.fn(),
}));
vi.mock("@/lib/api/apprise", () => api);

import { AppriseSection } from "@/components/settings/AppriseSection";

const wrap = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AppriseSection />
    </QueryClientProvider>,
  );

describe("AppriseSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listAppriseUrls.mockResolvedValue([]);
  });

  it("posts {label, apprise_url}", async () => {
    api.createAppriseUrl.mockResolvedValue({ id: "1" });
    wrap();
    await userEvent.type(screen.getByLabelText("Label"), "Phone");
    await userEvent.type(screen.getByLabelText("App URL"), "ntfy://ntfy.sh/t");
    await userEvent.click(screen.getByRole("button", { name: "Add app" }));
    await waitFor(() =>
      expect(api.createAppriseUrl).toHaveBeenCalledWith({
        label: "Phone",
        apprise_url: "ntfy://ntfy.sh/t",
      }),
    );
  });

  it("shows private-network message on apprise_url_blocked", async () => {
    api.createAppriseUrl.mockRejectedValue(
      new ApiError(422, "apprise_url_blocked", "blocked"),
    );
    wrap();
    await userEvent.type(screen.getByLabelText("App URL"), "ntfy://10.0.0.1/t");
    await userEvent.click(screen.getByRole("button", { name: "Add app" }));
    expect(
      await screen.findByText(
        "That address is on a private network. Ask an admin to allow it.",
      ),
    ).toBeInTheDocument();
  });

  it("lists apps with Test/Remove buttons", async () => {
    api.listAppriseUrls.mockResolvedValue([{ id: "1", label: "Phone" }]);
    wrap();
    expect(
      await screen.findByRole("button", { name: "Test Phone" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Remove Phone" }),
    ).toBeInTheDocument();
  });

  it("disables matrix apprise switch when hint given", () => {
    render(
      <NotificationMatrix
        types={[
          {
            key: "m",
            category: "c",
            default_channels: {},
            user_configurable: ["apprise"],
            digestable: false,
            label_i18n: "m",
          } as never,
        ]}
        prefs={{ notification_prefs: {}, digest_cadence: {} } as never}
        onChannel={vi.fn()}
        onCadence={vi.fn()}
        disabledChannels={{ apprise: "Add an app first" }}
      />,
    );
    expect(screen.getByRole("switch")).toBeDisabled();
  });
});
