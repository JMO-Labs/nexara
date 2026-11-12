/**
 * @file tests/unit/ui/Skeleton.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const reduced = vi.hoisted(() => ({ value: false }));
vi.mock("framer-motion", async (orig) => ({
  ...(await orig<typeof import("framer-motion")>()),
  useReducedMotion: () => reduced.value,
}));

import { Skeleton, skeletonVariants } from "@/components/ui/Skeleton";

describe("Skeleton", () => {
  beforeEach(() => {
    reduced.value = false;
  });

  it("exposes status role and aria-busy", () => {
    render(<Skeleton width={120} height={16} />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-busy", "true");
  });

  it("defines fade variants", () => {
    expect(skeletonVariants.initial).toEqual({ opacity: 0 });
    expect(skeletonVariants.animate).toMatchObject({
      opacity: 1,
      transition: { duration: 0.15, ease: "easeOut" },
    });
    expect(skeletonVariants.exit).toMatchObject({
      opacity: 0,
      transition: { duration: 0.1 },
    });
  });

  it("starts transparent to fade in on mount", () => {
    render(<Skeleton />);
    expect(screen.getByRole("status").style.opacity).toBe("0");
  });

  it("skips the fade under reduced motion", () => {
    reduced.value = true;
    render(<Skeleton />);
    expect(screen.getByRole("status").style.opacity).not.toBe("0");
  });

  it("keeps width, height and className", () => {
    render(<Skeleton width={50} height={8} className="x" />);
    const el = screen.getByRole("status");
    expect(el.style.width).toBe("50px");
    expect(el.style.height).toBe("8px");
    expect(el).toHaveClass("x");
  });
});
