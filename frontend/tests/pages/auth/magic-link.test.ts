/**
 * @file tests/pages/auth/magic-link.test.ts
 * @brief Tests for magic link request page.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import MagicLinkPage from "~/pages/auth/magic-link.vue";

const mockPost = vi.fn();
vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: vi.fn(),
    post: mockPost,
    put: vi.fn(),
    del: vi.fn(),
  }),
}));

describe("MagicLinkPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockPost.mockReset();
  });

  it("submits email and shows success", async () => {
    mockPost.mockResolvedValueOnce({ message: "ok" });

    const wrapper = mount(MagicLinkPage, {
      global: {
        stubs: {
          NuxtLayout: {
            template: "<div><slot /></div>",
          },
        },
      },
    });
    await wrapper.find("input#email").setValue("test@example.com");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith("/auth/magic-link/request", {
      email: "test@example.com",
    });
    expect(wrapper.text()).toContain("magic-link");
  });
});
