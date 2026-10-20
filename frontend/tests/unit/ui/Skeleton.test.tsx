/**
 * @file tests/unit/ui/Skeleton.test.tsx
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Skeleton } from "@/components/ui/Skeleton";

describe("Skeleton", () => {
  it("exposes status role and aria-busy", () => {
    render(<Skeleton width={120} height={16} />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-busy", "true");
  });
});
