/**
 * @file tests/unit/components/layout/PageTransition.test.tsx
 * @brief PageTransition renders children, keys on pathname, honours reduced motion.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

let pathname = "/app";
let reduced = false;
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});

import { PageTransition } from "@/components/layout/PageTransition";

describe("PageTransition", () => {
  beforeEach(() => {
    pathname = "/app";
    reduced = false;
  });

  it("renders children", () => {
    render(
      <PageTransition>
        <p>hello</p>
      </PageTransition>,
    );
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("keys the wrapper on pathname and fades via opacity", async () => {
    const { container, rerender } = render(
      <PageTransition>
        <p>a</p>
      </PageTransition>,
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.dataset.pathname).toBe("/app");
    expect(wrapper.style.opacity).toBe("1");
    pathname = "/app/chat";
    rerender(
      <PageTransition>
        <p>b</p>
      </PageTransition>,
    );
    // mode="wait": new node mounts only after the exit animation completes.
    await waitFor(() =>
      expect(
        container.querySelector('[data-pathname="/app/chat"]'),
      ).not.toBeNull(),
    );
  });

  it("skips animation when reduced motion is preferred", () => {
    reduced = true;
    pathname = "/app/chat";
    const { container, rerender } = render(
      <PageTransition>
        <p>a</p>
      </PageTransition>,
    );
    pathname = "/app/admin";
    rerender(
      <PageTransition>
        <p>b</p>
      </PageTransition>,
    );
    const els = container.querySelectorAll("[data-pathname]");
    expect(els).toHaveLength(1);
    expect((els[0] as HTMLElement).style.opacity).toBe("");
    expect(screen.getByText("b")).toBeInTheDocument();
  });
});
