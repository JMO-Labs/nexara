/**
 * @file tests/unit/components/Markdown.test.tsx
 * @brief Internal links navigate in-app (no target); external open new tab.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Markdown } from "@/components/ui/Markdown";

describe("Markdown links", () => {
  it("same-origin link has no target", () => {
    render(<Markdown content={`[x](${window.location.origin}/app/events)`} />);
    expect(screen.getByRole("link", { name: "x" })).not.toHaveAttribute(
      "target",
    );
  });
  it("/app path link has no target", () => {
    render(<Markdown content="[x](/app/chat)" />);
    expect(screen.getByRole("link", { name: "x" })).not.toHaveAttribute(
      "target",
    );
  });
  it("external link opens in new tab", () => {
    render(<Markdown content="[x](https://example.com)" />);
    expect(screen.getByRole("link", { name: "x" })).toHaveAttribute(
      "target",
      "_blank",
    );
  });
  it.each(["//evil.com", "/\\evil.com"])(
    "%s never becomes a same-tab off-site link",
    (href) => {
      render(<Markdown content={`[x](<${href}>)`} />);
      const a = screen.getByRole("link", { name: "x" });
      // Either opened as external, or encoded inert ("/%5Cevil.com").
      const raw = a.getAttribute("href") ?? "";
      if (a.getAttribute("target") !== "_blank")
        expect(raw).toMatch(/^\/(?![/\\])/);
    },
  );
});
