/**
 * @file tests/pages/auth/callback.test.ts
 * @brief Tests for OAuth callback page that exchanges code for tokens.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import AuthCallback from "~/pages/auth/callback.vue";

const mockFetchUser = vi.fn().mockResolvedValue(undefined);

let mockRouteQuery: Record<string, string> = {};

vi.mock("~/stores/auth", () => ({
  useAuthStore: () => ({
    accessToken: null,
    fetchUser: mockFetchUser,
  }),
}));

describe("auth/callback", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.stubGlobal("navigateTo", vi.fn());
    vi.stubGlobal("useRoute", () => ({
      path: "/auth/callback",
      params: {},
      query: mockRouteQuery,
      fullPath: "/auth/callback",
    }));
  });

  it("displays error when error query param is present", async () => {
    mockRouteQuery = { error: "access_denied" };

    const wrapper = mount(AuthCallback, {
      global: {
        stubs: {
          NuxtLayout: {
            template: "<div><slot /></div>",
          },
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("access_denied");
  });

  it("displays error when no code in query", async () => {
    mockRouteQuery = {};

    const wrapper = mount(AuthCallback, {
      global: {
        stubs: {
          NuxtLayout: {
            template: "<div><slot /></div>",
          },
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("auth.authenticationFailed");
  });

  it("shows loading spinner initially before mount callback completes", async () => {
    mockRouteQuery = { code: "test-code" };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() => new Promise(() => {})),
    );

    const wrapper = mount(AuthCallback, {
      global: {
        stubs: {
          NuxtLayout: {
            template: "<div><slot /></div>",
          },
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("auth.completing");
  });

  it("renders the back-to-login link on error", async () => {
    mockRouteQuery = { error: "invalid_request" };

    const wrapper = mount(AuthCallback, {
      global: {
        stubs: {
          NuxtLayout: {
            template: "<div><slot /></div>",
          },
        },
      },
    });
    await flushPromises();

    const link = wrapper.find('a[href="/auth/login"]');
    expect(link.exists()).toBe(true);
    expect(link.text()).toContain("auth.backToLogin");
  });
});
