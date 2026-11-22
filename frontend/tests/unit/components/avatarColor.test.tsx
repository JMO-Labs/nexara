/**
 * @file tests/unit/components/avatarColor.test.tsx
 * @brief Initials avatars get a stable per-person color that passes AA.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Avatar, AVATAR_COLORS, avatarColor } from "@/components/ui/Avatar";
import { contrastRatio } from "@/lib/contrast";

describe("avatarColor", () => {
  it("is stable per name and varies across names", () => {
    expect(avatarColor("Ruth Alvarez")).toBe(avatarColor("Ruth Alvarez"));
    const names = ["Ruth", "Leo", "Maya", "Nina", "Hannah", "Jordan", "Marcus"];
    expect(new Set(names.map(avatarColor)).size).toBeGreaterThan(2);
  });
  it("every fill keeps white initials at AA", () => {
    for (const c of AVATAR_COLORS)
      expect(contrastRatio("#FFFFFF", c)).toBeGreaterThanOrEqual(4.5);
  });
  it("paints the initials chip", () => {
    render(<Avatar name="Leo Soto" />);
    expect(
      screen.getByRole("img", { name: "Leo Soto" }).parentElement,
    ).toHaveStyle({
      background: avatarColor("Leo Soto"),
    });
  });
});
