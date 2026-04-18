/**
 * @file tests/components/feed/PollCreator.test.ts
 * @brief TDD tests for the PollCreator component.
 *
 * Verifies option inputs, add option button, and form structure.
 */

import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import PollCreator from "~/components/feed/PollCreator.vue";

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() }),
}));

describe("PollCreator", () => {
  it("starts with two empty options", () => {
    const wrapper = mount(PollCreator);
    const optionInputs = wrapper.findAll("[data-testid^=\"poll-option-\"]");
    expect(optionInputs.length).toBeGreaterThanOrEqual(2);
  });

  it("adds option on button click", async () => {
    const wrapper = mount(PollCreator);
    const addBtn = wrapper.find("[data-testid=\"add-option\"]");
    await addBtn.trigger("click");
    const options = wrapper.findAll("[data-testid^=\"poll-option-\"]");
    expect(options.length).toBeGreaterThanOrEqual(3);
  });
});
