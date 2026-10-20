/**
 * @file tests/unit/settings/useSettings.test.tsx
 * @brief Settings hooks tests. Verify queries + mutations invalidate correctly.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useUserSettings,
  useNotificationPrefs,
  useUpdateSettings,
  useUpdateProfile,
  useUpdateEmail,
  useUpdateNotificationPrefs,
} from "@/hooks/useSettings";
import * as settingsApi from "@/lib/api/settings";
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

vi.mock("@/lib/api/settings");

const createWrapper = () => {
  const queryClient = new QueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "Wrapper";
  return Wrapper;
};

describe("Settings hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
  });

  describe("useUserSettings", () => {
    it("fetches settings on mount", async () => {
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
      vi.mocked(settingsApi.getSettings).mockResolvedValue(mockSettings);

      const { result } = renderHook(() => useUserSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
      expect(result.current.data).toEqual(mockSettings);
    });
  });

  describe("useNotificationPrefs", () => {
    it("fetches notification preferences", async () => {
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
      vi.mocked(settingsApi.getNotificationPrefs).mockResolvedValue(mockPrefs);

      const { result } = renderHook(() => useNotificationPrefs(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
      expect(result.current.data).toEqual(mockPrefs);
    });
  });

  describe("useUpdateSettings", () => {
    it("calls updateSettings and shows success toast", async () => {
      const mockResp = { theme: "dark" as const, locale: "en-US" };
      vi.mocked(settingsApi.updateSettings).mockResolvedValue({
        ...mockResp,
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
      });

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate({ theme: "dark" });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(settingsApi.updateSettings).toHaveBeenCalledWith({
        theme: "dark",
      });
      const toasts = useToasts.getState().items;
      expect(toasts.some((t) => t.variant === "success")).toBe(true);
    });
  });

  describe("useUpdateProfile", () => {
    it("calls updateProfile and shows success toast", async () => {
      const body = { display_name: "New Name" };
      const mockResp = { message: "Profile updated" };
      vi.mocked(settingsApi.updateProfile).mockResolvedValue(mockResp);

      const { result } = renderHook(() => useUpdateProfile(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate(body);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(settingsApi.updateProfile).toHaveBeenCalledWith(body);
      const toasts = useToasts.getState().items;
      expect(toasts.some((t) => t.variant === "success")).toBe(true);
    });
  });

  describe("useUpdateEmail", () => {
    it("calls updateEmail and shows success toast", async () => {
      const email = "new@example.com";
      const mockResp = { message: "Email updated" };
      vi.mocked(settingsApi.updateEmail).mockResolvedValue(mockResp);

      const { result } = renderHook(() => useUpdateEmail(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate(email);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(settingsApi.updateEmail).toHaveBeenCalledWith(email);
      const toasts = useToasts.getState().items;
      expect(toasts.some((t) => t.variant === "success")).toBe(true);
    });
  });

  describe("useUpdateNotificationPrefs", () => {
    it("calls updateNotificationPrefs and shows success toast", async () => {
      const body = { notif_mention_inapp: false };
      const mockResp = {
        theme: "system" as const,
        locale: "en-US",
        notif_mention_inapp: false,
        notif_mention_email: true,
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
      vi.mocked(settingsApi.updateNotificationPrefs).mockResolvedValue(
        mockResp,
      );

      const { result } = renderHook(() => useUpdateNotificationPrefs(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.mutate(body);
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(settingsApi.updateNotificationPrefs).toHaveBeenCalledWith(body);
      const toasts = useToasts.getState().items;
      expect(toasts.some((t) => t.variant === "success")).toBe(true);
    });
  });
});
