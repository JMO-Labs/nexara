/**
 * @file tests/components/settings/LinkedAccounts.test.ts
 * @brief Tests for LinkedAccounts placeholder component.
 */
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LinkedAccounts from "~/components/settings/LinkedAccounts.vue";

describe("LinkedAccounts", () => {
  it("renders heading text", () => {
    const wrapper = mount(LinkedAccounts);
    expect(wrapper.text()).toContain("settings.linkedAccounts");
  });

  it("renders placeholder text", () => {
    const wrapper = mount(LinkedAccounts);
    expect(wrapper.text()).toContain("settings.linkedAccountsPlaceholder");
  });
});
