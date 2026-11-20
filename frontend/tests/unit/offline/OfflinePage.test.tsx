/**
 * @file tests/unit/offline/OfflinePage.test.tsx
 * @brief Offline page uses the brand glass panel, EmptyState pattern and an ink retry pill.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import OfflinePage from "@/app/offline/page";

describe("OfflinePage", () => {
  it("renders a glass panel with brand lockup and medium-weight title", () => {
    render(<OfflinePage />);
    expect(screen.getByLabelText("Nexara")).toBeTruthy();
    const title = screen.getByRole("heading", { level: 1 });
    expect(title).toHaveClass("font-medium", "text-2xl");
    expect(title.closest(".glass")).not.toBeNull();
    expect(title.closest(".glass")!.className).toContain("rounded-[32px]");
  });

  it("shows a glyph in a soft circle and an ink pill retry", () => {
    const { container } = render(<OfflinePage />);
    const circle = container.querySelector(".glass-item.rounded-full");
    expect(circle).not.toBeNull();
    expect(circle!.querySelector("svg")).not.toBeNull();
    const retry = screen.getByRole("link", { name: "Retry" });
    expect(retry).toHaveAttribute("href", "/app");
    expect(retry.className).toContain("bg-surface-strong");
  });
});
