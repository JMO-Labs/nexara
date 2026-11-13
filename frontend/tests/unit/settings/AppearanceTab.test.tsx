/**
 * @file tests/unit/settings/AppearanceTab.test.tsx
 * @brief AppearanceTab component tests. Verify theme and locale selectors.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppearanceTab } from "@/components/settings/AppearanceTab";
import { useUI } from "@/stores/ui";
import * as settingsHooks from "@/hooks/useSettings";

vi.mock("@/hooks/useSettings");
const setTheme = vi.fn();
vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: "system", setTheme }),
}));

const mockSettings = {
  theme: "system" as const,
  locale: "en-US",
  font_size: "medium" as const,
  compact_feed: false,
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
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
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

  it("offers System, Light, Dark and applies the choice", async () => {
    const mutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateSettings).mockReturnValue({
      mutate,
      isPending: false,
    } as any);
    render(<AppearanceTab />, { wrapper: createWrapper() });

    expect(
      within(screen.getByRole("radiogroup", { name: "Theme" })).getAllByRole(
        "radio",
      ),
    ).toHaveLength(3);
    expect(screen.getByRole("radio", { name: "System" })).toBeChecked();
    await userEvent.setup().click(screen.getByRole("radio", { name: "Dark" }));
    await waitFor(() => expect(setTheme).toHaveBeenCalledWith("dark"));
    expect(mutate).toHaveBeenCalledWith({ theme: "dark" });
  });

  it("offers font size radios and a compact feed switch that save", async () => {
    const mutate = vi.fn();
    vi.mocked(settingsHooks.useUpdateSettings).mockReturnValue({
      mutate,
      isPending: false,
    } as any);
    render(<AppearanceTab />, { wrapper: createWrapper() });
    const user = userEvent.setup();

    expect(screen.getByRole("radio", { name: "Medium" })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Large" }));
    expect(mutate).toHaveBeenCalledWith({ font_size: "large" });

    await user.click(screen.getByRole("switch", { name: "Compact feed" }));
    expect(mutate).toHaveBeenCalledWith({ compact_feed: true });
  });

  it("shows a live preview", () => {
    render(<AppearanceTab />, { wrapper: createWrapper() });
    expect(screen.getByTestId("appearance-preview")).toHaveAttribute(
      "data-font-size",
      "medium",
    );
  });

  it("renders language selector", () => {
    render(<AppearanceTab />, { wrapper: createWrapper() });

    const labels = screen.getAllByText(/language/i);
    expect(labels.length).toBeGreaterThan(0);
  });

  it("binds a Comfortable/Compact control to the UI store", async () => {
    useUI.setState({ density: "comfortable" });
    render(<AppearanceTab />, { wrapper: createWrapper() });

    const group = screen.getByRole("radiogroup", { name: "Density" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Comfortable" })).toBeChecked();
    await userEvent
      .setup()
      .click(screen.getByRole("radio", { name: "Compact" }));
    await waitFor(() => expect(useUI.getState().density).toBe("compact"));
  });
});
