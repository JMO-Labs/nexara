/**
 * @file tests/unit/components/auth/AuthCard.test.tsx
 * @brief AuthCard: full-page split with brand lockup, title and the
 *        decorative mosaic (hidden from assistive tech).
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthCard } from "@/components/auth/AuthCard";

describe("AuthCard", () => {
  it("fills the page as a two-column split from md up", () => {
    render(
      <AuthCard title="T">
        <p>x</p>
      </AuthCard>,
    );
    const root = screen
      .getByRole("heading", { name: "T" })
      .closest("[data-auth-card-root]");
    expect(root).not.toBeNull();
    expect(root!.className).toContain("min-h-dvh");
    expect(root!.className).toContain("md:grid-cols-");
  });

  it("shows title, subtitle and footer; the art is aria-hidden", () => {
    const { container } = render(
      <AuthCard title="T" subtitle="Sub" footer={<span>Foot</span>}>
        <p>x</p>
      </AuthCard>,
    );
    expect(screen.getByRole("heading", { name: "T" })).toBeInTheDocument();
    expect(screen.getByText("Sub").className).toContain("text-muted");
    expect(screen.getByText("Foot")).toBeInTheDocument();
    expect(container.querySelector("svg[aria-hidden]")).not.toBeNull();
  });

  it("shows the brand lockup instead of a bold text wordmark", () => {
    render(
      <AuthCard title="T">
        <p>x</p>
      </AuthCard>,
    );
    expect(screen.getByLabelText("Nexara")).toBeTruthy();
  });
});
