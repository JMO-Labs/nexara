/**
 * @file tests/unit/components/auth/AuthCard.test.tsx
 * @brief AuthCard is a centered 400px-max column with a glass panel and brand lockup.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthCard } from "@/components/auth/AuthCard";

describe("AuthCard", () => {
  it("caps width at 400px and centers", () => {
    render(
      <AuthCard title="T">
        <p>x</p>
      </AuthCard>,
    );
    const root = screen
      .getByRole("heading", { name: "T" })
      .closest("[data-auth-card-root]");
    expect(root).not.toBeNull();
    expect(root!.className).toContain("max-w-[400px]");
    expect(root!.className).toContain("mx-auto");
    expect(root!.className).toContain("w-full");
  });

  it("uses a glass panel with a 32px radius and medium-weight title", () => {
    render(
      <AuthCard title="T" subtitle="Sub">
        <p>x</p>
      </AuthCard>,
    );
    const panel = screen.getByRole("heading", { name: "T" }).closest(".glass");
    expect(panel).not.toBeNull();
    expect(panel!.className).toContain("rounded-[32px]");
    expect(screen.getByRole("heading", { name: "T" }).className).toContain(
      "font-medium",
    );
    expect(screen.getByText("Sub").className).toContain("text-muted");
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
