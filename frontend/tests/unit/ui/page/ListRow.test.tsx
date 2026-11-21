/**
 * @file tests/unit/ui/page/ListRow.test.tsx
 * @brief ListRow variants.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ListRow } from "@/components/ui/page";

describe("ListRow", () => {
  it("href renders a link", () => {
    render(<ListRow href="/app/x">Row</ListRow>);
    const a = screen.getByRole("link", { name: "Row" });
    expect(a).toHaveAttribute("href", "/app/x");
    expect(a).toHaveClass("glass-item", "rounded-[22px]");
  });
  it("onClick renders a button", async () => {
    const fn = vi.fn();
    render(<ListRow onClick={fn}>Row</ListRow>);
    await userEvent.click(screen.getByRole("button", { name: "Row" }));
    expect(fn).toHaveBeenCalled();
  });
  it("selected adds ring and aria-current", () => {
    render(
      <ListRow onClick={() => {}} selected>
        Row
      </ListRow>,
    );
    const b = screen.getByRole("button");
    expect(b).toHaveClass("ring-2");
    expect(b).toHaveAttribute("aria-current", "true");
  });
  it("plain renders a div", () => {
    render(<ListRow data-testid="r">Row</ListRow>);
    expect(screen.getByTestId("r").tagName).toBe("DIV");
  });
});
