/**
 * @file tests/unit/auth/OAuthButtons.test.tsx
 * @brief SSO buttons: "Continue with" label, preset glyph, aria-hidden.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OAuthButtons } from "@/components/auth/OAuthButtons";

describe("OAuthButtons", () => {
  it("labels links and renders preset glyph hidden from AT", () => {
    render(
      <OAuthButtons
        providers={[
          {
            slug: "g",
            display_name: "Google",
            icon_url: null,
            preset: "google",
          },
          { slug: "x", display_name: "Corp", icon_url: null, preset: "custom" },
        ]}
      />,
    );
    const link = screen.getByRole("link", { name: "Continue with Google" });
    expect(link).toBeInTheDocument();
    expect(screen.getByTestId("sso-glyph-google")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
    expect(
      screen.getByRole("link", { name: "Continue with Corp" }),
    ).toBeInTheDocument();
  });

  it("renders nothing without providers", () => {
    const { container } = render(<OAuthButtons providers={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
