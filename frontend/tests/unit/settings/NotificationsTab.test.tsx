/**
 * @file tests/unit/settings/NotificationsTab.test.tsx
 * @brief NotificationsTab component tests. Verify toggle switches.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { NotificationsTab } from "@/components/settings/NotificationsTab";
import * as settingsHooks from "@/hooks/useSettings";
import { useToasts } from "@/stores/toasts";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "toasts.settings.saved": "Settings saved",
      "toasts.errors.generic": "Something went wrong",
    };
    return translations[key] || key;
  },
}));

vi.mock("@/hooks/useSettings");

const mockPrefs = {
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
    <CssVarsProvider theme={joyTheme}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </CssVarsProvider>
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
});
