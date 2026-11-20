/**
 * @file tests/unit/home/HomeTile.test.tsx
 * @brief HomeTile: accordion header semantics and pointer sheen.
 */
import { describe, it, expect, vi } from "vitest";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/app",
}));
import { render, screen, fireEvent } from "@testing-library/react";
import { Calendar } from "lucide-react";
import { HomeTile } from "@/components/home/HomeTile";

function tile(over: Partial<React.ComponentProps<typeof HomeTile>> = {}) {
  return (
    <HomeTile
      id="next"
      title="Up next"
      icon={Calendar}
      href="/app/events"
      linkLabel="See calendar"
      summary="Potluck, Sat"
      count={2}
      hot
      open={false}
      onToggle={() => {}}
      {...over}
    >
      <p>tile body</p>
    </HomeTile>
  );
}

describe("HomeTile", () => {
  it("collapsed: button aria-expanded=false, summary and count shown, body hidden below md", () => {
    render(tile());
    const btn = screen.getByRole("button", { name: /Up next/ });
    expect(btn).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Potluck, Sat")).toBeInTheDocument();
    const badge = screen.getByLabelText("2 need you");
    expect(badge.className).toContain("--nx-red");
    const body = screen.getByText("tile body").parentElement!;
    expect(body.className).toContain("hidden");
    expect(body.className).toContain("md:flex");
    expect(btn.getAttribute("aria-controls")).toBe(body.id);
  });

  it("open: body visible, expanded true, blue 'new' badge when not hot", () => {
    render(tile({ open: true, hot: false }));
    expect(screen.getByRole("button", { name: /Up next/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    const body = screen.getByText("tile body").parentElement!;
    expect(body.className).not.toMatch(/(^|\s)hidden(\s|$)/);
    expect(screen.getByLabelText("2 new").className).toContain(
      "bg-surface-strong",
    );
    expect(screen.getByLabelText("2 new").className).not.toContain("--nx-blue");
  });

  it("calls onToggle with id", () => {
    const onToggle = vi.fn();
    render(tile({ onToggle }));
    fireEvent.click(screen.getByRole("button", { name: /Up next/ }));
    expect(onToggle).toHaveBeenCalledWith("next");
  });

  it("renders a header link for md+", () => {
    render(tile());
    expect(screen.getByRole("link", { name: "See calendar" })).toHaveAttribute(
      "href",
      "/app/events",
    );
  });

  it("lifts on hover via glass-lift", () => {
    const { container } = render(tile());
    expect(container.querySelector("section")).toHaveClass("glass-lift");
  });
});
