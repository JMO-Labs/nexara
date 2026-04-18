/**
 * @file tests/components/profile/InterestTagInput.test.ts
 * @brief Tests for InterestTagInput component.
 */
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import InterestTagInput from "~/components/profile/InterestTagInput.vue";

describe("InterestTagInput", () => {
  const categories = [
    {
      slug: "hobbies",
      label: "Hobbies",
      description: null,
      icon: null,
      multi_value: true,
      sort_order: 10,
    },
  ];

  it("emits add event on submit", async () => {
    const wrapper = mount(InterestTagInput, { props: { categories } });

    const select = wrapper.find("select");
    await select.setValue("hobbies");
    const input = wrapper.find('input[type="text"]');
    await input.setValue("Hiking");
    await wrapper.find("form").trigger("submit.prevent");

    expect(wrapper.emitted("add")).toBeTruthy();
  });
});
