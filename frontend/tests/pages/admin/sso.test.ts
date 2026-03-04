/**
 * @file tests/pages/admin/sso.test.ts
 * @brief Tests for admin SSO providers management page.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import SsoPage from "~/pages/app/admin/sso.vue";

const mockGet = vi.fn().mockResolvedValue([]);

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    del: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock("~/stores/ui", () => ({
  useUiStore: () => ({
    showToast: vi.fn(),
  }),
}));

describe("admin/sso", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockGet.mockResolvedValue([]);
  });

  it("renders SSO heading text", async () => {
    const wrapper = mount(SsoPage, {
      global: {
        stubs: { AdminSsoProviderForm: true },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("admin.sso");
  });

  it("shows add provider button", async () => {
    const wrapper = mount(SsoPage, {
      global: {
        stubs: { AdminSsoProviderForm: true },
      },
    });
    await flushPromises();

    const addBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("admin.addProvider"));
    expect(addBtn).toBeDefined();
  });

  it("shows table headers", async () => {
    const wrapper = mount(SsoPage, {
      global: {
        stubs: { AdminSsoProviderForm: true },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("admin.displayName");
    expect(wrapper.text()).toContain("admin.providerType");
    expect(wrapper.text()).toContain("admin.slug");
    expect(wrapper.text()).toContain("admin.status");
    expect(wrapper.text()).toContain("admin.actions");
  });

  it("shows no_results when providers list is empty", async () => {
    const wrapper = mount(SsoPage, {
      global: {
        stubs: { AdminSsoProviderForm: true },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("admin.no_results");
  });
});
