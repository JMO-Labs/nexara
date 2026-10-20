/**
 * @file tests/unit/settings/settingsApi.test.ts
 * @brief Settings API endpoint tests. Verify method, path, body shape.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import * as settingsApi from "@/lib/api/settings";
import * as client from "@/lib/api/client";

vi.mock("@/lib/api/client");

describe("Settings API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getSettings", () => {
    it("calls GET /api/v1/settings", async () => {
      const mockData = {
        theme: "system" as const,
        locale: "en-US",
        notif_mention_inapp: true,
        notif_mention_email: false,
      };
      vi.mocked(client.apiGet).mockResolvedValue(mockData);

      const result = await settingsApi.getSettings();

      expect(client.apiGet).toHaveBeenCalledWith("/api/v1/settings");
      expect(result).toEqual(mockData);
    });
  });

  describe("updateSettings", () => {
    it("calls PUT /api/v1/settings with body", async () => {
      const body = { theme: "dark" as const };
      const mockResp = { theme: "dark" as const, locale: "en-US" };
      vi.mocked(client.apiPut).mockResolvedValue(mockResp);

      const result = await settingsApi.updateSettings(body);

      expect(client.apiPut).toHaveBeenCalledWith("/api/v1/settings", body);
      expect(result).toEqual(mockResp);
    });
  });

  describe("getNotificationPrefs", () => {
    it("calls GET /api/v1/settings/notifications", async () => {
      const mockData = {
        notif_mention_inapp: true,
        notif_mention_email: false,
      };
      vi.mocked(client.apiGet).mockResolvedValue(mockData);

      const result = await settingsApi.getNotificationPrefs();

      expect(client.apiGet).toHaveBeenCalledWith(
        "/api/v1/settings/notifications",
      );
      expect(result).toEqual(mockData);
    });
  });

  describe("updateNotificationPrefs", () => {
    it("calls PUT /api/v1/settings/notifications with body", async () => {
      const body = { notif_mention_inapp: false };
      const mockResp = {
        notif_mention_inapp: false,
        notif_mention_email: true,
      };
      vi.mocked(client.apiPut).mockResolvedValue(mockResp);

      const result = await settingsApi.updateNotificationPrefs(body);

      expect(client.apiPut).toHaveBeenCalledWith(
        "/api/v1/settings/notifications",
        body,
      );
      expect(result).toEqual(mockResp);
    });
  });

  describe("updateProfile", () => {
    it("calls PUT /api/v1/settings/profile with body", async () => {
      const body = { display_name: "New Name", bio: "Bio" };
      const mockResp = { message: "Profile updated" };
      vi.mocked(client.apiPut).mockResolvedValue(mockResp);

      const result = await settingsApi.updateProfile(body);

      expect(client.apiPut).toHaveBeenCalledWith(
        "/api/v1/settings/profile",
        body,
      );
      expect(result).toEqual(mockResp);
    });
  });

  describe("updateEmail", () => {
    it("calls PUT /api/v1/settings/email with email body", async () => {
      const email = "new@example.com";
      const mockResp = { message: "Email updated" };
      vi.mocked(client.apiPut).mockResolvedValue(mockResp);

      const result = await settingsApi.updateEmail(email);

      expect(client.apiPut).toHaveBeenCalledWith("/api/v1/settings/email", {
        email,
      });
      expect(result).toEqual(mockResp);
    });
  });
});
