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
import type { PrivacyAppearanceSettings } from "@/lib/api/settings";
import { useToasts } from "@/stores/toasts";
import { qk } from "@/lib/query-keys";

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

const privacy: PrivacyAppearanceSettings = {
  profile_visible_to: "community",
  show_online_status: true,
  show_last_seen: true,
  show_birthday_to: "community",
  show_birthday_year: false,
  allow_sassybot: false,
  font_size: "medium",
  compact_feed: false,
};

const createWrapper = () => {
  const queryClient = new QueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "Wrapper";
  return Wrapper;
};

const PRIVACY: settingsApi.PrivacyAppearanceSettings = {
  profile_visible_to: "community",
  show_online_status: true,
  show_last_seen: true,
  show_birthday_to: "community",
  show_birthday_year: false,
  allow_sassybot: true,
  font_size: "medium",
  compact_feed: false,
};

describe("Settings hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
  });

  describe("useUserSettings", () => {
    it("fetches settings on mount", async () => {
      const mockSettings = {
        ...PRIVACY,
        theme: "system" as const,
        locale: "en-US",
        ...privacy,
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
        ...PRIVACY,
        ...mockResp,
        ...privacy,
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

  describe("useUpdateSettings optimistic behaviour", () => {
    const base = {
      theme: "system" as const,
      locale: "en-US",
      compact_feed: false,
    } as unknown as settingsApi.UserSettings;
    const key = qk.settings.profile();

    const setup = () => {
      const qc = new QueryClient();
      qc.setQueryData(key, base);
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      );
      const hook = renderHook(() => useUpdateSettings(), { wrapper });
      return { qc, hook };
    };

    it("updates cache before the request resolves", async () => {
      let resolve!: (v: settingsApi.UserSettings) => void;
      vi.mocked(settingsApi.updateSettings).mockReturnValue(
        new Promise((r) => {
          resolve = r;
        }),
      );
      const { qc, hook } = setup();
      act(() => {
        hook.result.current.mutate({ compact_feed: true } as never);
      });
      await waitFor(() => {
        expect(
          (qc.getQueryData(key) as { compact_feed: boolean }).compact_feed,
        ).toBe(true);
      });
      expect(hook.result.current.isPending).toBe(true);
      resolve({ ...base, compact_feed: true } as never);
      await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));
    });

    it("rolls back and pushes danger toast on failure", async () => {
      vi.mocked(settingsApi.updateSettings).mockRejectedValue(
        new Error("boom"),
      );
      const { qc, hook } = setup();
      act(() => {
        hook.result.current.mutate({ compact_feed: true } as never);
      });
      await waitFor(() => expect(hook.result.current.isError).toBe(true));
      expect(
        (qc.getQueryData(key) as { compact_feed: boolean }).compact_feed,
      ).toBe(false);
      expect(
        useToasts.getState().items.some((t) => t.variant === "danger"),
      ).toBe(true);
    });

    it("invalidates the settings key on settled", async () => {
      vi.mocked(settingsApi.updateSettings).mockResolvedValue(base);
      const { qc, hook } = setup();
      const spy = vi.spyOn(qc, "invalidateQueries");
      act(() => {
        hook.result.current.mutate({ compact_feed: true } as never);
      });
      await waitFor(() => expect(hook.result.current.isSuccess).toBe(true));
      expect(spy).toHaveBeenCalledWith({ queryKey: key });
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
        ...PRIVACY,
        theme: "system" as const,
        locale: "en-US",
        ...privacy,
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
