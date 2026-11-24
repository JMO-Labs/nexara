/**
 * @file tests/unit/admin/AlertsTab.test.tsx
 * @brief Alerts tab: admin endpoints, scheme-only rows, local-address switch.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const client = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
  seg: (s: string) => s,
}));
vi.mock("@/lib/api/client", () => client);

import { AlertsTab } from "@/components/admin/AlertsTab";

const B = "/api/v1/admin/apprise";
const target = {
  id: "t1",
  label: "Phone",
  enabled: true,
  scheme: "ntfy",
  failure_count: 0,
  last_failure_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <AlertsTab />
    </QueryClientProvider>,
  );
}

describe("AlertsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.apiGet.mockImplementation(async (u: string) =>
      u === `${B}/targets` ? [target] : { allow_local: false },
    );
    client.apiPut.mockResolvedValue({ allow_local: true });
    client.apiPost.mockResolvedValue({ status: "sent", message: "ok" });
    client.apiDelete.mockResolvedValue({});
  });

  it("lists targets with scheme only", async () => {
    renderTab();
    expect(await screen.findByText("Phone")).toBeInTheDocument();
    expect(screen.getByText("ntfy://…")).toBeInTheDocument();
  });

  it("switch PUTs allow_local", async () => {
    renderTab();
    fireEvent.click(
      await screen.findByRole("switch", {
        name: "Let members use local addresses",
      }),
    );
    await waitFor(() =>
      expect(client.apiPut).toHaveBeenCalledWith(`${B}/settings`, {
        allow_local: true,
      }),
    );
  });

  it("adds a target via the admin endpoint", async () => {
    renderTab();
    fireEvent.change(await screen.findByLabelText("Apprise URL"), {
      target: { value: "ntfy://192.168.1.10/topic" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add target" }));
    await waitFor(() =>
      expect(client.apiPost).toHaveBeenCalledWith(`${B}/targets`, {
        apprise_url: "ntfy://192.168.1.10/topic",
      }),
    );
  });

  it("tests and removes a target", async () => {
    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Test Phone" }));
    await waitFor(() =>
      expect(client.apiPost).toHaveBeenCalledWith(`${B}/targets/t1/test`),
    );
    fireEvent.click(screen.getByRole("button", { name: "Remove Phone" }));
    await waitFor(() =>
      expect(client.apiDelete).toHaveBeenCalledWith(`${B}/targets/t1`),
    );
  });
});
