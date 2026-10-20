/**
 * @file tests/unit/chat/TypingIndicator.test.tsx
 * @brief Typing indicator text for 0, 1, many.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TypingIndicator } from "@/components/chat/TypingIndicator";

describe("TypingIndicator", () => {
  it("renders nothing for 0", () => {
    const { container } = render(<TypingIndicator count={0} />);
    expect(container).toBeEmptyDOMElement();
  });
  it("singular text", () => {
    render(<TypingIndicator count={1} />);
    expect(screen.getByText("Someone is typing…")).toBeInTheDocument();
  });
  it("plural text", () => {
    render(<TypingIndicator count={3} />);
    expect(screen.getByText("3 people are typing…")).toBeInTheDocument();
  });
});
