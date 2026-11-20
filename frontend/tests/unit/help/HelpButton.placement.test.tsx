/**
 * @file tests/unit/help/HelpButton.placement.test.tsx
 * @brief HelpButton is a glass circle and hides on chat routes so it cannot
 *        cover the composer send button.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const nav = vi.hoisted(() => ({ path: "/app/home" as string | null }));
vi.mock("next/navigation", () => ({ usePathname: () => nav.path }));

import { HelpButton } from "@/components/help/HelpButton";

describe("HelpButton placement and style", () => {
  it("is a glass circle without the solid shadow or hover scale", () => {
    nav.path = "/app/home";
    render(<HelpButton />);
    const btn = screen.getByRole("button", { name: "Help menu" });
    expect(btn).toHaveClass("glass-btn", "rounded-full", "size-11");
    expect(btn.className).not.toContain("shadow-md");
    expect(btn.className).not.toContain("hover:scale-110");
    expect(btn.className).not.toContain("bg-surface-strong");
  });

  it("is hidden on chat routes", () => {
    nav.path = "/app/chat";
    render(<HelpButton />);
    expect(screen.queryByRole("button", { name: "Help menu" })).toBeNull();
  });
});
