/**
 * @file tests/components/admin/ColorPicker.test.ts
 * @brief Tests for ColorPicker component.
 */
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ColorPicker from "~/components/admin/ColorPicker.vue";

describe("ColorPicker", () => {
  it("renders label and color swatch", () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: "#3b82f6", label: "Primary Color" },
    });

    expect(wrapper.text()).toContain("Primary Color");
    expect(wrapper.find('[data-testid="color-swatch"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="color-input"]').exists()).toBe(true);
  });

  it("displays swatch with the current color", () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: "#ff0000", label: "Color" },
    });

    const swatch = wrapper.find('[data-testid="color-swatch"]');
    expect(swatch.attributes("style")).toContain("background-color");
  });

  it("emits update:modelValue on hex text change", async () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: "#3b82f6", label: "Color" },
    });

    const textInput = wrapper.find('[data-testid="hex-input"]');
    await textInput.setValue("#ff0000");
    await textInput.trigger("change");

    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
  });

  it("shows contrast info when contrastAgainst provided", () => {
    const wrapper = mount(ColorPicker, {
      props: {
        modelValue: "#000000",
        label: "Text",
        contrastAgainst: "#ffffff",
      },
    });

    expect(wrapper.find("[data-testid=\"contrast-ratio\"]").exists()).toBe(true);
  });

  it("uses monospace font for hex input", () => {
    const wrapper = mount(ColorPicker, {
      props: { modelValue: "#3b82f6", label: "Color" },
    });

    const hexInput = wrapper.find('[data-testid="hex-input"]');
    expect(hexInput.classes()).toContain("font-mono");
  });
});
