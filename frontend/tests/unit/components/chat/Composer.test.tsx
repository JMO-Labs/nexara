/**
 * @file tests/unit/components/chat/Composer.test.tsx
 * @brief Composer: Enter/Ctrl+Enter send, Shift+Enter newline, emoji, attach, focus handle.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { Composer, type ComposerHandle } from "@/components/chat/Composer";

const type = (text: string) =>
  fireEvent.change(screen.getByLabelText("Message"), {
    target: { value: text },
  });

describe("Composer", () => {
  it("sends on Enter", () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    type("hi");
    fireEvent.keyDown(screen.getByLabelText("Message"), { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("hi");
  });
  it("sends on Ctrl+Enter and Cmd+Enter", () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    type("a");
    fireEvent.keyDown(screen.getByLabelText("Message"), {
      key: "Enter",
      ctrlKey: true,
    });
    type("b");
    fireEvent.keyDown(screen.getByLabelText("Message"), {
      key: "Enter",
      metaKey: true,
    });
    expect(onSend).toHaveBeenNthCalledWith(1, "a");
    expect(onSend).toHaveBeenNthCalledWith(2, "b");
  });
  it("does not send on Shift+Enter", () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    type("a");
    fireEvent.keyDown(screen.getByLabelText("Message"), {
      key: "Enter",
      shiftKey: true,
    });
    expect(onSend).not.toHaveBeenCalled();
  });
  it("inserts an emoji from the picker", () => {
    render(<Composer onSend={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Add emoji" }));
    fireEvent.click(screen.getByRole("button", { name: "Insert 🎉" }));
    expect(
      (screen.getByLabelText("Message") as HTMLTextAreaElement).value,
    ).toBe("🎉");
  });
  it("attach button calls handler", () => {
    const onAttach = vi.fn();
    render(<Composer onSend={() => {}} onAttachMedia={onAttach} />);
    fireEvent.click(screen.getByRole("button", { name: "Attach media" }));
    expect(onAttach).toHaveBeenCalled();
  });
  it("exposes focus() via ref", () => {
    const ref = React.createRef<ComposerHandle>();
    render(<Composer ref={ref} onSend={() => {}} />);
    act(() => ref.current?.focus());
    expect(document.activeElement).toBe(screen.getByLabelText("Message"));
  });
});
