/**
 * @file tests/unit/feed/ReactionRow.test.tsx
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ReactionRow } from "@/components/feed/ReactionRow";

function wrap(ui: React.ReactNode) {
  return render(ui);
}

describe("ReactionRow", () => {
  it("renders existing reactions and fires onReact", async () => {
    const onReact = vi.fn();
    wrap(
      <ReactionRow
        reactions={[{ emoji: "👍", count: 3, reacted_by_me: false }]}
        commentCount={2}
        onReact={onReact}
      />,
    );
    expect(screen.getByText(/👍 3/)).toBeInTheDocument();
    const chipBtn = screen.getByRole("button", { name: /👍/ });
    fireEvent.click(chipBtn);
    expect(onReact).toHaveBeenCalledWith("👍");
  });

  it("shows comment count", () => {
    wrap(<ReactionRow reactions={[]} commentCount={7} onReact={() => {}} />);
    expect(screen.getByText("7")).toBeInTheDocument();
  });
});
