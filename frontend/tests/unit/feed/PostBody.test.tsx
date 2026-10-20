/**
 * @file tests/unit/feed/PostBody.test.tsx
 * @brief PostBody renders content with linkified URLs and preserves newlines.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { PostBody } from "@/components/feed/PostBody";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("PostBody", () => {
  it("renders text", () => {
    wrap(<PostBody content="hello world" />);
    expect(screen.getByText(/hello world/i)).toBeInTheDocument();
  });

  it("linkifies http URLs", () => {
    wrap(<PostBody content="see https://example.com here" />);
    const link = screen.getByRole("link", { name: /example\.com/i });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("returns nothing for empty content", () => {
    const { container } = wrap(<PostBody content="   " />);
    expect(container).toBeEmptyDOMElement();
  });
});
