/**
 * @file tests/components/subgroups/SubgroupCard.test.ts
 * @brief Tests for the SubgroupCard component.
 *
 * Verifies name/description/policy rendering, private badge,
 * fallback initials, and routing to the subgroup detail page.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import SubgroupCard from "~/components/subgroups/SubgroupCard.vue";
import type { Subgroup } from "~/types/api";

const baseSubgroup: Subgroup = {
  id: "sg-1",
  name: "Photography Pros",
  slug: "photography-pros",
  description: "All things lenses and light",
  avatar_url: null,
  is_private: false,
  join_policy: "open",
  created_by: "user-1",
  archived_at: null,
  created_at: "2026-04-01T10:00:00Z",
  updated_at: "2026-04-01T10:00:00Z",
};

const stubs = {
  NuxtLink: {
    template: '<a :href="to"><slot /></a>',
    props: ["to"],
  },
};

describe("SubgroupCard", () => {
  it("renders the subgroup name", () => {
    const wrapper = mount(SubgroupCard, {
      props: { subgroup: baseSubgroup },
      global: { stubs },
    });

    expect(wrapper.find('[data-testid="subgroup-card-name"]').text()).toBe(
      "Photography Pros",
    );
  });

  it("renders the slug prefixed with /", () => {
    const wrapper = mount(SubgroupCard, {
      props: { subgroup: baseSubgroup },
      global: { stubs },
    });

    expect(wrapper.text()).toContain("/photography-pros");
  });

  it("renders the description when present", () => {
    const wrapper = mount(SubgroupCard, {
      props: { subgroup: baseSubgroup },
      global: { stubs },
    });

    expect(
      wrapper.find('[data-testid="subgroup-card-description"]').text(),
    ).toBe("All things lenses and light");
  });

  it("omits the description block when description is null", () => {
    const wrapper = mount(SubgroupCard, {
      props: { subgroup: { ...baseSubgroup, description: null } },
      global: { stubs },
    });

    expect(
      wrapper.find('[data-testid="subgroup-card-description"]').exists(),
    ).toBe(false);
  });

  it("shows the private badge only when subgroup is private", () => {
    const open = mount(SubgroupCard, {
      props: { subgroup: baseSubgroup },
      global: { stubs },
    });
    const priv = mount(SubgroupCard, {
      props: { subgroup: { ...baseSubgroup, is_private: true } },
      global: { stubs },
    });

    expect(open.find('[data-testid="subgroup-card-private"]').exists()).toBe(
      false,
    );
    expect(priv.find('[data-testid="subgroup-card-private"]').exists()).toBe(
      true,
    );
  });

  it("renders the avatar image when avatar_url is set", () => {
    const wrapper = mount(SubgroupCard, {
      props: {
        subgroup: { ...baseSubgroup, avatar_url: "/img/sg.png" },
      },
      global: { stubs },
    });

    const img = wrapper.find("img");
    expect(img.exists()).toBe(true);
    expect(img.attributes("src")).toBe("/img/sg.png");
  });

  it("renders two-letter initials when avatar is missing", () => {
    const wrapper = mount(SubgroupCard, {
      props: { subgroup: baseSubgroup },
      global: { stubs },
    });

    expect(wrapper.text()).toContain("PP");
  });

  it("uses single-letter initial when name is one word", () => {
    const wrapper = mount(SubgroupCard, {
      props: {
        subgroup: { ...baseSubgroup, name: "Lensheads" },
      },
      global: { stubs },
    });

    expect(wrapper.text()).toContain("L");
  });

  it("includes the join policy short label", () => {
    const wrapper = mount(SubgroupCard, {
      props: { subgroup: baseSubgroup },
      global: { stubs },
    });

    expect(
      wrapper.find('[data-testid="subgroup-card-policy"]').text(),
    ).toContain("subgroups.policyShort.open");
  });

  it("links to the subgroup detail route", () => {
    const wrapper = mount(SubgroupCard, {
      props: { subgroup: baseSubgroup },
      global: { stubs },
    });

    expect(wrapper.find("a").attributes("href")).toBe(
      "/app/subgroups/photography-pros",
    );
  });
});
