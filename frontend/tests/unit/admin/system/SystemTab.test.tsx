/**
 * @file tests/unit/admin/system/SystemTab.test.tsx
 * @brief System tab: status words, polling interval, disk progressbar.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const client = vi.hoisted(() => ({ apiGet: vi.fn() }));
vi.mock("@/lib/api/client", () => client);

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
    client.apiGet.mockResolvedValue(data);
    renderTab();
    await screen.findByText("Down");
    const q = qc.getQueryCache().find({ queryKey: ["admin", "system"] });
    expect(
      (q?.observers[0].options as { refetchInterval: number }).refetchInterval,
    ).toBe(30_000);
  });

  it("renders disk bar with aria values and % text", async () => {
    client.apiGet.mockResolvedValue(data);
    renderTab();
    const bar = await screen.findByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "86");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
    expect(screen.getByText(/86% used/)).toBeInTheDocument();
  });

  it("shows Grafana link only when URL present", async () => {
    client.apiGet.mockResolvedValue({ ...data, grafana_url: "http://g/x" });
    renderTab();
    const a = await screen.findByRole("link", { name: /Open Grafana/ });
    expect(a).toHaveAttribute("href", "http://g/x");
  });

  it("omits Grafana link and bar for external storage", async () => {
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
