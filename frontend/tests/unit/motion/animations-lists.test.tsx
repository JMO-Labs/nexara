/**
 * @file tests/unit/motion/animations-lists.test.tsx
 * @brief Admin KPI and feed list animations + reduced motion.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

let reduced = false;
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/hooks/useAdmin", () => ({
  useAdminMetrics: () => ({
    isLoading: false,
    error: null,
    data: {
      community: {
        users_total: 3,
        users_active_30d: 2,
        posts_last_7d: 1,
        media_storage_bytes: 10,
        users_online_now: 1,
        posts_total: 5,
        media_files: 2,
      },
      system: { version: "1", uptime_seconds: 5 },
      waf: { blocks_today: 0, blocks_by_reason: {} },
    },
  }),
}));

import { MetricsTab } from "@/components/admin/MetricsTab";

beforeEach(() => {
  reduced = false;
});

describe("MetricsTab KPI stagger", () => {
  it("cards start hidden and stagger in", () => {
    render(<MetricsTab />);
    const cards = screen.getAllByTestId("metric-card");
    expect(cards.length).toBeGreaterThan(4);
    expect(cards[0]).toHaveStyle({ opacity: "0" });
  });
  it("renders instantly under reduced motion", () => {
    reduced = true;
    render(<MetricsTab />);
    expect(screen.getAllByTestId("metric-card")[0].style.opacity).toBe("");
  });
});
