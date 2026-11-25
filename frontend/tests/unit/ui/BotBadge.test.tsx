/**
 * @file tests/unit/ui/BotBadge.test.tsx
 * @brief BotBadge labels.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BotBadge } from "@/components/ui/BotBadge";

describe("BotBadge", () => {
  it("renders Bot", () => {
    render(<BotBadge />);
    expect(screen.getByText("Bot")).toBeInTheDocument();
  });
  it("renders Bot (inactive)", () => {
    render(<BotBadge active={false} />);
    expect(screen.getByText("Bot (inactive)")).toBeInTheDocument();
  });
});
