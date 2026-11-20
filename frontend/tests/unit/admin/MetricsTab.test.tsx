/**
 * @file tests/unit/admin/MetricsTab.test.tsx
 * @brief MetricsTab: glass panels, KPI tiles and stat rows.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MetricsTab } from "@/components/admin/MetricsTab";

vi.mock("@/hooks/useAdmin", () => ({
  useAdminMetrics: () => ({
    isLoading: false,
    error: null,
    data: {
      community: {
        users_total: 12,
        users_active_30d: 7,
        posts_last_7d: 3,
        media_storage_bytes: 2048,
        users_online_now: 2,
        posts_total: 99,
        media_files: 5,
      },
      system: {
        version: "1.2.3",
        uptime_seconds: 90000,
        db_size_bytes: 1048576,
        celery_queue_depth: 0,
      },
      waf: { blocks_today: 4, blocks_by_reason: { sqli: 3 } },
    },
  }),
}));

describe("MetricsTab", () => {
  it("groups stats into titled glass panels", () => {
    render(<MetricsTab />);
    for (const name of ["Overview", "Community", "System"])
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "System" }).closest("section")
        ?.className,
    ).toMatch(/glass/);
  });

  it("merges WAF blocks into the System panel and formats uptime", () => {
    render(<MetricsTab />);
    const system = screen
      .getByRole("heading", { name: "System" })
      .closest("section") as HTMLElement;
    expect(
      within(system).getByText("Blocked requests today"),
    ).toBeInTheDocument();
    expect(within(system).getByText("1d 1h")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /WAF/ })).toBeNull();
  });

  it("renders KPI tiles as glass-item with tabular numbers", () => {
    render(<MetricsTab />);
    const kpi = screen
      .getByRole("heading", { name: "Overview" })
      .closest("section") as HTMLElement;
    const tiles = within(kpi).getAllByTestId("metric-card");
    expect(tiles).toHaveLength(4);
    expect(tiles[0].className).toMatch(/glass-item/);
    expect(within(tiles[0]).getByText("12").className).toMatch(/tabular-nums/);
  });

  it("renders system stats as label/value rows", () => {
    render(<MetricsTab />);
    const sys = screen
      .getByRole("heading", { name: "System" })
      .closest("section") as HTMLElement;
    expect(within(sys).getByText("Version")).toBeInTheDocument();
    expect(within(sys).getByText("1.2.3").className).toMatch(/tabular-nums/);
    expect(within(sys).getByText("1d 1h")).toBeInTheDocument();
  });

  it("does not use bare Card surfaces", () => {
    const { container } = render(<MetricsTab />);
    expect(container.innerHTML).not.toMatch(/bg-white|rounded-\[24px\]/);
  });
});
