/**
 * @file tests/unit/settings/NotificationsTab.test.tsx
 * @brief NotificationsTab component tests. Verify toggle switches.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationsTab } from "@/components/settings/NotificationsTab";
import * as settingsHooks from "@/hooks/useSettings";
import { useToasts } from "@/stores/toasts";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "toasts.settings.saved": "Settings saved",
      "toasts.errors.generic": "Something went wrong",
      matrix: "Apprise",
    };
    return translations[key] || key;
  },
}));

vi.mock("@/hooks/useSettings");
const apprise = vi.hoisted(() => ({ data: [] as { enabled: boolean }[] }));
vi.mock("@/components/settings/AppriseList", () => ({
  AppriseList: () => null,
  useAppriseUrls: () => ({ data: apprise.data }),
}));

const TYPES = [
  "mention",
  "comment",
  "reaction",
  "new_post",
  "system",
  "invite_accepted",
  "event_reminder",
  "event_rsvp",
  "gallery_activity",
  "prompt",
  "prompt_summary",
  "poll",
  "dm",
  "birthday",
];
const allFields = Object.fromEntries(
  TYPES.flatMap((t) =>
    ["inapp", "email", "push"].map((c) => [`notif_${t}_${c}`, false]),
  ),
);

const mockPrefs = {
  ...allFields,
  mute_all_push: false,
  email_digest_enabled: false,
  email_digest_hour: 8,
  notif_mention_inapp: true,
  notif_mention_email: false,
  notif_comment_inapp: true,
  notif_comment_email: false,
  notif_reaction_inapp: true,
  notif_reaction_email: false,
  notif_new_post_inapp: true,
  notif_new_post_email: false,
  notif_system_inapp: true,
  notif_system_email: false,
  notif_invite_accepted_inapp: true,
  notif_invite_accepted_email: false,
  mute_all_email: false,
};

const createWrapper = () => {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("NotificationsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    vi.mocked(settingsHooks.useNotificationPrefs).mockReturnValue({
      data: mockPrefs,
      isLoading: false,
      isSuccess: true,
    } as any);
    vi.mocked(settingsHooks.useUpdateNotificationPrefs).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);
  });

  it("shows Apprise column only with an enabled URL", () => {
    apprise.data = [{ enabled: true }];
    const { unmount } = render(<NotificationsTab />, {
      wrapper: createWrapper(),
    });
    expect(
      screen.getByRole("switch", { name: "Mention Apprise" }),
    ).toBeInTheDocument();
    unmount();
    for (const data of [[], [{ enabled: false }]]) {
      apprise.data = data;
      const r = render(<NotificationsTab />, { wrapper: createWrapper() });
      expect(
        screen.queryByRole("switch", { name: "Mention Apprise" }),
      ).not.toBeInTheDocument();
      r.unmount();
    }
    apprise.data = [];
  });

  it("renders notification preference toggles", () => {
    render(<NotificationsTab />, { wrapper: createWrapper() });

    expect(screen.getByText(/mention/i)).toBeInTheDocument();
    expect(screen.getByText(/comment/i)).toBeInTheDocument();
  });

  it("toggles a notification preference", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateNotificationPrefs).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);

    render(<NotificationsTab />, { wrapper: createWrapper() });

    const switches = screen.getAllByRole("switch");
    await user.click(switches[0]);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalled();
    });
  });

  it("shows mute all email toggle", () => {
    render(<NotificationsTab />, { wrapper: createWrapper() });

    expect(screen.getByText(/mute all email/i)).toBeInTheDocument();
  });

  const setup = () => {
    const mutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateNotificationPrefs).mockReturnValue({
      mutate,
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);
    render(<NotificationsTab />, { wrapper: createWrapper() });
    return mutate;
  };

  it("renders 14 rows with three switches each", () => {
    setup();
    for (const ch of ["In-app", "Email", "Push"]) {
      expect(
        screen.getByRole("switch", { name: `Direct message ${ch}` }),
      ).toBeInTheDocument();
    }
    expect(
      screen.getByRole("switch", { name: "Birthday Push" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("switch", { name: / Push$/ })).toHaveLength(14);
    expect(screen.getAllByRole("switch", { name: / In-app$/ })).toHaveLength(
      14,
    );
  });

  it("toggles a push switch with only that field", async () => {
    const mutate = setup();
    await userEvent
      .setup()
      .click(screen.getByRole("switch", { name: "Direct message Push" }));
    await waitFor(() =>
      expect(mutate).toHaveBeenCalledWith({ notif_dm_push: true }),
    );
  });

  it("toggles mute all push with only that field", async () => {
    const mutate = setup();
    await userEvent
      .setup()
      .click(screen.getByRole("switch", { name: "Mute all push" }));
    await waitFor(() =>
      expect(mutate).toHaveBeenCalledWith({ mute_all_push: true }),
    );
  });

  it("enables digest and disables hour select while off", async () => {
    const mutate = setup();
    expect(
      screen.getByRole("combobox", { name: "Digest hour" }),
    ).toBeDisabled();
    await userEvent
      .setup()
      .click(screen.getByRole("switch", { name: "Email digest" }));
    await waitFor(() =>
      expect(mutate).toHaveBeenCalledWith({ email_digest_enabled: true }),
    );
  });

  it("enables hour select when digest is on", () => {
    vi.mocked(settingsHooks.useNotificationPrefs).mockReturnValue({
      data: { ...mockPrefs, email_digest_enabled: true },
      isLoading: false,
      isSuccess: true,
    } as any);
    setup();
    expect(screen.getByRole("combobox", { name: "Digest hour" })).toBeEnabled();
  });
});
