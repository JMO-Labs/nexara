/**
 * @file tests/unit/chat/Composer.test.tsx
 * @brief Composer Enter-sends, Shift+Enter newlines, debounces typing.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Composer } from "@/components/chat/Composer";

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

describe("Composer", () => {
  it("sends on Enter", () => {
    const onSend = vi.fn();
    wrap(<Composer onSend={onSend} />);
    const ta = screen.getByPlaceholderText(/write a message/i);
    fireEvent.change(ta, { target: { value: "hi" } });
    fireEvent.keyDown(ta, { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("hi");
  });

  it("inserts newline on Shift+Enter", () => {
    const onSend = vi.fn();
    wrap(<Composer onSend={onSend} />);
    const ta = screen.getByPlaceholderText(/write a message/i);
    fireEvent.change(ta, { target: { value: "a" } });
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables send for empty content", () => {
    const onSend = vi.fn();
    wrap(<Composer onSend={onSend} />);
    const btn = screen.getByLabelText(/send message/i);
    expect(btn).toBeDisabled();
  });

  it("emits typing on first keystroke", () => {
    const onTyping = vi.fn();
    wrap(<Composer onSend={() => {}} onTyping={onTyping} />);
    const ta = screen.getByPlaceholderText(/write a message/i);
    fireEvent.change(ta, { target: { value: "h" } });
    expect(onTyping).toHaveBeenCalledTimes(1);
  });
});
