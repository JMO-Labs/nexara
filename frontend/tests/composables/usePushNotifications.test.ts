/**
 * @file tests/composables/usePushNotifications.test.ts
 * @brief Tests for usePushNotifications composable.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDel = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: mockGet, post: mockPost, put: vi.fn(), del: mockDel }),
}));

describe("usePushNotifications", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it("reports unsupported when PushManager missing", async () => {
    const { usePushNotifications } = await import(
      "~/composables/usePushNotifications"
    );
    const { isSupported } = usePushNotifications();
    expect(isSupported.value).toBe(false);
  });
});
