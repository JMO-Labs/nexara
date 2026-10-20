/**
 * @file tests/unit/settings/AppearanceTab.test.tsx
 * @brief AppearanceTab component tests. Verify theme and locale selectors.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { AppearanceTab } from "@/components/settings/AppearanceTab";
import * as settingsHooks from "@/hooks/useSettings";

vi.mock("@/hooks/useSettings");
vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "system",
    setTheme: vi.fn(),
  }),
}));

const mockSettings = {
  theme: "system" as const,
  locale: "en-US",
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
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <CssVarsProvider theme={joyTheme}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </CssVarsProvider>
  );
  Wrapper.displayName = "Wrapper";
  return Wrapper;
};

describe("AppearanceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(settingsHooks.useUserSettings).mockReturnValue({
      data: mockSettings,
      isLoading: false,
      isSuccess: true,
    } as any);
    vi.mocked(settingsHooks.useUpdateSettings).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);
  });

  it("renders theme selector", () => {
    render(<AppearanceTab />, { wrapper: createWrapper() });

    expect(screen.getByText(/appearance/i)).toBeInTheDocument();
    const labels = screen.getAllByText(/theme/i);
    expect(labels.length).toBeGreaterThan(0);
  });

  it("renders language selector", () => {
    render(<AppearanceTab />, { wrapper: createWrapper() });

    const labels = screen.getAllByText(/language/i);
    expect(labels.length).toBeGreaterThan(0);
  });
});
