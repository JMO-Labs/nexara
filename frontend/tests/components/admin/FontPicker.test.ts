/**
 * @file tests/components/admin/FontPicker.test.ts
 * @brief Tests for FontPicker component.
 */
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import FontPicker from "~/components/admin/FontPicker.vue";

describe("FontPicker", () => {
  it("renders label and select", () => {
    const wrapper = mount(FontPicker, {
      props: { modelValue: "Inter", label: "Font Family" },
    });

    expect(wrapper.text()).toContain("Font Family");
    expect(wrapper.find("select").exists()).toBe(true);
  });

  it("shows preview text in selected font", () => {
    const wrapper = mount(FontPicker, {
      props: { modelValue: "Roboto", label: "Font" },
    });

    const preview = wrapper.find("[data-testid=\"font-preview\"]");
    expect(preview.exists()).toBe(true);
  });

  it("emits update:modelValue on selection", async () => {
    const wrapper = mount(FontPicker, {
      props: { modelValue: "Inter", label: "Font" },
    });

    await wrapper.find("select").setValue("Roboto");

    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
  });
});
