/**
 * @file tests/unit/components/auth/AuthCard.test.tsx
 * @brief AuthCard is a centered 400px-max column.
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
});
