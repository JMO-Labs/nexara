/**
 * @file tests/unit/admin/system/SystemTab.test.tsx
 * @brief System tab: status words, polling interval, disk progressbar.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const client = vi.hoisted(() => ({ apiGet: vi.fn() }));
vi.mock("@/lib/api/client", () => client);

import { DISK_WARN_PCT } from "@/components/admin/system/DiskPanel";
import { formatUptime } from "@/components/admin/system/RuntimePanel";
import { SystemTab } from "@/components/admin/system/SystemTab";

const data = {
  components: [
    { name: "Database", status: "ok", detail: "" },
    { name: "Worker", status: "down", detail: "no heartbeat" },
    { name: "Mail", status: "warn", detail: "slow" },
  ],
  disk: {
    external: false,
    total_bytes: 1000,
    used_bytes: 860,
    used_pct: 86,
    db_bytes: 2048,
    top_tables: [{ name: "posts", bytes: 1024 }],
  },
  runtime: {
    version: "1.2.3",
    alembic_head: "0067",
    uptime_seconds: 90061,
    cpu_percent: 12.4,
    mem_total_bytes: 2048,
    mem_used_bytes: 1024,
    mem_limit_bytes: null,
  },
};

let qc: QueryClient;
function renderTab() {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <SystemTab />
    </QueryClientProvider>,
  );
}

describe("formatUptime", () => {
  it("formats minutes, hours and days", () => {
    expect(formatUptime(59)).toBe("0m");
    expect(formatUptime(3660)).toBe("1h 1m");
    expect(formatUptime(90061)).toBe("1d 1h 1m");
  });
});

describe("SystemTab", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows icon+word status for each component", async () => {
    client.apiGet.mockResolvedValue(data);
    renderTab();
    expect(await screen.findByText("Down")).toBeInTheDocument();
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(client.apiGet).toHaveBeenCalledWith("/api/v1/admin/system");
  });

  it("polls every 30s", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      client.apiGet.mockResolvedValue(data);
      renderTab();
      await screen.findByText("Down");
      expect(client.apiGet).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(30_000);
      await waitFor(() => expect(client.apiGet).toHaveBeenCalledTimes(2));
    } finally {
      vi.useRealTimers();
    }
  });

  it("renders disk bar with aria values and % text", async () => {
    client.apiGet.mockResolvedValue(data);
    renderTab();
    const bar = await screen.findByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "86");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
    expect(screen.getByText(/86% used/)).toBeInTheDocument();
    expect(bar).toHaveAttribute("aria-valuetext", "86% used, 860 B of 1000 B");
  });

  it("shows Grafana link only when URL present", async () => {
    client.apiGet.mockResolvedValue({ ...data, grafana_url: "http://g/x" });
    renderTab();
    const a = await screen.findByRole("link", { name: /Open Grafana/ });
    expect(a).toHaveAttribute("href", "http://g/x");
  });

  it("omits Grafana link when no URL or non-http URL", async () => {
    client.apiGet.mockResolvedValue({ ...data, grafana_url: "javascript:x" });
    renderTab();
    await screen.findByText("Down");
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("falls back to Needs attention for unknown status", async () => {
    client.apiGet.mockResolvedValue({
      ...data,
      components: [{ name: "Odd", status: "weird", detail: "" }],
    });
    renderTab();
    expect(await screen.findByText("Needs attention")).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "System components" }),
    ).toBeInTheDocument();
  });

  it.each([
    [DISK_WARN_PCT - 1, "bg-accent"],
    [DISK_WARN_PCT, "bg-danger"],
  ])("bar at %s%% uses %s", async (pct, cls) => {
    client.apiGet.mockResolvedValue({
      ...data,
      disk: { ...data.disk, used_pct: pct },
    });
    renderTab();
    const bar = await screen.findByRole("progressbar");
    expect(bar.firstElementChild).toHaveClass(cls);
  });

  it("omits the disk bar for external storage", async () => {
    client.apiGet.mockResolvedValue({
      ...data,
      disk: { ...data.disk, external: true, used_pct: null },
    });
    renderTab();
    await screen.findByText("Down");
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("shows error notice on failure", async () => {
    client.apiGet.mockRejectedValue(new Error("boom"));
    renderTab();
    expect(await screen.findByRole("alert")).toHaveTextContent(/Failed/);
  });
});
