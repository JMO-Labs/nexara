/**
 * @file Logo.test.tsx
 * @brief Tests for brand logo components.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BrandLockup, Wordmark } from "@/components/brand/Logo";

describe("Logo", () => {
  it("BrandLockup without logoUrl renders svg and wordmark", () => {
    const { container } = render(<BrandLockup name="Maple" />);
    expect(container.querySelector("svg")).not.toBeNull();
    expect(container.textContent).toContain("nexara");
  });

  it("BrandLockup with logoUrl renders custom img", () => {
    render(<BrandLockup name="Maple" logoUrl="/x.png" />);
    expect(screen.getByAltText("Maple")).toBeInTheDocument();
  });

  it("Wordmark ara span is font-light", () => {
    render(<Wordmark />);
    expect(screen.getByText("ara").className).toContain("font-light");
  });
});
