/**
 * @file tests/components/profile/InterestsTab.test.ts
 * @brief Tests for InterestsTab component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import InterestsTab from "~/components/profile/InterestsTab.vue";
import InterestTagInput from "~/components/profile/InterestTagInput.vue";

const mockGet = vi.fn();
const mockDel = vi.fn();
vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: mockGet, post: vi.fn(), put: vi.fn(), del: mockDel }),
}));

describe("InterestsTab", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockGet.mockReset();
    mockDel.mockReset();
  });

  it("renders grouped interests", async () => {
    mockGet.mockResolvedValueOnce({
      interests: [
        {
          id: "1",
          user_id: "u1",
          category_slug: "hobbies",
          value: "Hiking",
          source: "manual",
          confidence: 1,
          created_at: "2026-01-01",
        },
      ],
      categories: [
        {
          slug: "hobbies",
          label: "Hobbies",
          description: null,
          icon: null,
          multi_value: true,
          sort_order: 10,
        },
      ],
    });

    const wrapper = mount(InterestsTab, {
      props: { userId: "u1", isOwner: false },
      global: {
        components: { ProfileInterestTagInput: InterestTagInput },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Hobbies");
    expect(wrapper.text()).toContain("Hiking");
  });

  it("shows add input when owner", async () => {
    mockGet.mockResolvedValueOnce({ interests: [], categories: [] });

    const wrapper = mount(InterestsTab, {
      props: { userId: "u1", isOwner: true },
      global: {
        components: { ProfileInterestTagInput: InterestTagInput },
      },
    });
    await flushPromises();

    expect(
      wrapper.findComponent({ name: "InterestTagInput" }).exists() ||
        wrapper.find('[data-testid="interest-add"]').exists(),
    ).toBe(true);
  });
});
