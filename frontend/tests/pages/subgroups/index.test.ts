/**
 * @file tests/pages/subgroups/index.test.ts
 * @brief Tests for the subgroups directory page.
 *
 * Verifies fetchList runs on mount, search filter, empty state,
 * card grid rendering, and create button toggling the modal.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import SubgroupsIndexPage from "~/pages/app/subgroups/index.vue";
import { useSubgroupsStore } from "~/stores/subgroups";
import type { Subgroup } from "~/types/api";

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPost,
    put: vi.fn(),
    del: vi.fn(),
  }),
}));

const stubs = {
  NuxtLink: {
    template: '<a :href="to"><slot /></a>',
    props: ["to"],
  },
  Teleport: { template: "<div><slot /></div>" },
};

const fixtureA: Subgroup = {
  id: "sg-1",
  name: "Photographers",
  slug: "photographers",
  description: "Lenses",
  avatar_url: null,
  is_private: false,
  join_policy: "open",
  created_by: null,
  archived_at: null,
  created_at: "2026-04-01T10:00:00Z",
  updated_at: "2026-04-01T10:00:00Z",
};

const fixtureB: Subgroup = {
  ...fixtureA,
  id: "sg-2",
  name: "Bookworms",
  slug: "bookworms",
  description: "Reading club",
};

describe("SubgroupsIndexPage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("calls fetchList on mount and renders cards", async () => {
    mockGet.mockResolvedValueOnce([fixtureA, fixtureB]);

    const wrapper = mount(SubgroupsIndexPage, { global: { stubs } });
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith("/subgroups");
    expect(wrapper.find('[data-testid="subgroups-grid"]').exists()).toBe(true);
    expect(
      wrapper.find('[data-testid="subgroup-card-photographers"]').exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-testid="subgroup-card-bookworms"]').exists(),
    ).toBe(true);
  });

  it("shows empty state when fetch returns no subgroups", async () => {
    mockGet.mockResolvedValueOnce([]);

    const wrapper = mount(SubgroupsIndexPage, { global: { stubs } });
    await flushPromises();

    expect(wrapper.find('[data-testid="subgroups-empty"]').exists()).toBe(
      true,
    );
  });

  it("filters cards using the search input", async () => {
    mockGet.mockResolvedValueOnce([fixtureA, fixtureB]);
    const wrapper = mount(SubgroupsIndexPage, { global: { stubs } });
    await flushPromises();

    await wrapper
      .get('[data-testid="subgroups-search"]')
      .setValue("book");

    expect(
      wrapper.find('[data-testid="subgroup-card-photographers"]').exists(),
    ).toBe(false);
    expect(
      wrapper.find('[data-testid="subgroup-card-bookworms"]').exists(),
    ).toBe(true);
  });

  it("opens the create modal when the create button is clicked", async () => {
    mockGet.mockResolvedValueOnce([]);
    const wrapper = mount(SubgroupsIndexPage, { global: { stubs } });
    await flushPromises();

    expect(
      wrapper.find('[data-testid="subgroups-create-modal"]').exists(),
    ).toBe(false);

    await wrapper
      .get('[data-testid="subgroups-create-button"]')
      .trigger("click");

    expect(
      wrapper.find('[data-testid="subgroups-create-modal"]').exists(),
    ).toBe(true);
  });

  it("rejects an invalid slug in the create form", async () => {
    mockGet.mockResolvedValueOnce([]);
    const store = useSubgroupsStore();
    const createSpy = vi.spyOn(store, "createSubgroup");

    const wrapper = mount(SubgroupsIndexPage, { global: { stubs } });
    await flushPromises();

    await wrapper
      .get('[data-testid="subgroups-create-button"]')
      .trigger("click");

    await wrapper.find("#sg_name").setValue("My Group");
    await wrapper.find("#sg_slug").setValue("INVALID Slug!");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(createSpy).not.toHaveBeenCalled();
  });
});
