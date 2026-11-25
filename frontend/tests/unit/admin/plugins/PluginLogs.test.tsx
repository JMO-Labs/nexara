/**
 * @file tests/unit/admin/plugins/PluginLogs.test.tsx
 * @brief Host-run plugins: logs panel, status badge, host error copy and the
 *        package install mode.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/errors";

const client = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  seg: (s: string) => s,
}));
vi.mock("@/lib/api/client", () => client);
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ user: { community_id: "c1" } }),
}));

import { PluginLogs } from "@/components/admin/plugins/PluginLogs";
import { PluginDetail } from "@/components/admin/plugins/PluginDetail";
import { InstallUrlDialog } from "@/components/admin/plugins/InstallUrlDialog";

const SHA = "a".repeat(64);
const plugin = {
  id: "i1",
  plugin_id: "echo",
  name: "Echo",
  version: "1.0.0",
  status: "installing",
  scopes: [],
  events: [],
  egress: [],
  enabled: true,
  bot_user_id: "b1",
  settings_schema: {},
  source: "package",
  host_status: "sandbox_unavailable",
  host_error: "sandbox_unavailable",
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => vi.clearAllMocks());

describe("PluginLogs", () => {
  it("shows lines in a <pre> and refreshes", async () => {
    client.apiGet
      .mockResolvedValueOnce({ lines: ["[echo] ready", "[echo] got mention"] })
      .mockResolvedValueOnce({ lines: ["[echo] later"] });
    wrap(<PluginLogs pluginId="echo" />);
    const pre = await screen.findByLabelText("Plugin log");
    expect(pre.tagName).toBe("PRE");
    await waitFor(() =>
      expect(pre).toHaveTextContent("[echo] ready [echo] got mention"),
    );
    expect(client.apiGet).toHaveBeenCalledWith("/api/v1/plugins/echo/logs");
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(pre).toHaveTextContent("[echo] later"));
  });

  it("shows an empty state", async () => {
    client.apiGet.mockResolvedValue({ lines: [] });
    wrap(<PluginLogs pluginId="echo" />);
    expect(await screen.findByText("No output yet.")).toBeInTheDocument();
  });

  it("shows host errors as an alert", async () => {
    client.apiGet.mockRejectedValue(
      new ApiError(503, "plugin_host_unavailable", "Host down"),
    );
    wrap(<PluginLogs pluginId="echo" />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});

describe("PluginDetail (package)", () => {
  it("shows host status with icon text, plain error copy and logs", async () => {
    client.apiGet.mockImplementation(async (u: string) =>
      u.endsWith("/settings")
        ? {}
        : u.endsWith("/logs")
          ? { lines: ["boot"] }
          : [plugin],
    );
    wrap(<PluginDetail pluginId="echo" />);
    expect(await screen.findByText("Sandbox unavailable")).toBeInTheDocument();
    expect(
      screen.getByText(/plugin sandbox cannot start on this server/),
    ).toBeInTheDocument();
    expect(await screen.findByLabelText("Plugin log")).toBeInTheDocument();
  });
});

describe("InstallUrlDialog (package mode)", () => {
  it("sends package URL and sha256 by default", async () => {
    client.apiPost.mockResolvedValueOnce(plugin);
    const onClose = vi.fn();
    wrap(<InstallUrlDialog open onClose={onClose} />);
    fireEvent.change(screen.getByLabelText("Package URL"), {
      target: { value: "https://x/echo.tgz" },
    });
    fireEvent.change(screen.getByLabelText("SHA-256"), {
      target: { value: SHA },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(client.apiPost).toHaveBeenCalledWith("/api/v1/plugins/install", {
      source: "package",
      package_url: "https://x/echo.tgz",
      sha256: SHA,
      approved_scopes: [],
    });
  });

  it("explains a missing plugin host", async () => {
    client.apiPost.mockRejectedValueOnce(
      new ApiError(422, "plugin_host_not_configured", "no host"),
    );
    wrap(<InstallUrlDialog open onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Package URL"), {
      target: { value: "https://x/echo.tgz" },
    });
    fireEvent.change(screen.getByLabelText("SHA-256"), {
      target: { value: SHA },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText(/need the plugin host/)).toBeInTheDocument();
  });
});
