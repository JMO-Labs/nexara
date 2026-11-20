/**
 * @file tests/unit/chat/ThreadRow.test.tsx
 * @brief ThreadRow selected state is a soft glass tint, not a hard ring.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ThreadRow } from "@/components/chat/ThreadRow";

describe("ThreadRow", () => {
  it("shows a soft selected state without a hard ring", () => {
    render(
      <ThreadRow
        name="Garden"
        preview="hi"
        color="var(--nx-blue)"
        selected
        onClick={vi.fn()}
      />,
    );
    const row = screen.getByRole("button", { name: /garden/i });
    expect(row).toHaveAttribute("aria-current", "true");
    expect(row.className).not.toContain("ring-2");
    expect(row.className).not.toContain("ring-ink");
    expect(row.className).toContain("color-mix");
  });

  it("uses a round icon tile", () => {
    const { container } = render(
      <ThreadRow
        name="Garden"
        preview="hi"
        color="var(--nx-blue)"
        onClick={vi.fn()}
      />,
    );
    const tile = container.querySelector("button > span") as HTMLElement;
    expect(tile.className).toContain("rounded-full");
    expect(tile.className).not.toContain("rounded-[14px]");
  });
});
