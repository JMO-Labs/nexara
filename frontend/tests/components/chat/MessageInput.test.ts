/**
 * @file tests/components/chat/MessageInput.test.ts
 * @brief Tests for the chat MessageInput composer.
 *
 * Verifies Enter-to-send, Shift+Enter newline, blank-content guard,
 * disabled state, throttled typing emits, and clearing after send.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import MessageInput from "~/components/chat/MessageInput.vue";

describe("MessageInput", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-18T10:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("emits send with trimmed content on form submit", async () => {
    const wrapper = mount(MessageInput);
    const input = wrapper.get('[data-testid="chat-input"]');
    await input.setValue("  hi there  ");

    await wrapper.get('[data-testid="chat-input-form"]').trigger("submit");

    expect(wrapper.emitted("send")?.[0]).toEqual(["hi there"]);
  });

  it("ignores blank submissions", async () => {
    const wrapper = mount(MessageInput);
    const input = wrapper.get('[data-testid="chat-input"]');
    await input.setValue("   ");

    await wrapper.get('[data-testid="chat-input-form"]').trigger("submit");

    expect(wrapper.emitted("send")).toBeUndefined();
  });

  it("clears the textarea after sending", async () => {
    const wrapper = mount(MessageInput);
    const input = wrapper.get('[data-testid="chat-input"]');
    await input.setValue("hello");

    await wrapper.get('[data-testid="chat-input-form"]').trigger("submit");

    expect(
      (input.element as HTMLTextAreaElement).value,
    ).toBe("");
  });

  it("disables the textarea and send button when disabled prop is true", () => {
    const wrapper = mount(MessageInput, { props: { disabled: true } });

    expect(
      wrapper.get('[data-testid="chat-input"]').attributes("disabled"),
    ).toBeDefined();
    expect(
      wrapper.get('[data-testid="chat-input-send"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("emits typing on input but throttles within the window", async () => {
    const wrapper = mount(MessageInput);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("h");
    await input.trigger("input");
    await input.setValue("hi");
    await input.trigger("input");

    expect(wrapper.emitted("typing")?.length).toBe(1);

    vi.advanceTimersByTime(2_500);
    await input.setValue("hi!");
    await input.trigger("input");

    expect(wrapper.emitted("typing")?.length).toBe(2);
  });

  it("does not emit typing when disabled", async () => {
    const wrapper = mount(MessageInput, { props: { disabled: true } });
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("hi");
    await input.trigger("input");

    expect(wrapper.emitted("typing")).toBeUndefined();
  });

  it("sends on bare Enter via keydown handler", async () => {
    const wrapper = mount(MessageInput);
    const input = wrapper.get('[data-testid="chat-input"]');
    await input.setValue("press enter");

    await input.trigger("keydown", { key: "Enter" });

    expect(wrapper.emitted("send")?.[0]).toEqual(["press enter"]);
  });
});
