/**
 * @file tests/unit/admin/plugins/plugins.test.tsx
 * @brief Installed plugins: install approval flow, uninstall, credentials, detail.
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

import { InstallUrlDialog } from "@/components/admin/plugins/InstallUrlDialog";
import { UninstallDialog } from "@/components/admin/plugins/UninstallDialog";
import { CredentialsDialog } from "@/components/admin/plugins/CredentialsDialog";
import { InstalledTab } from "@/components/admin/plugins/InstalledTab";
import { PluginDetail } from "@/components/admin/plugins/PluginDetail";

const plugin = {
  id: "i1",
  plugin_id: "echo",
  name: "Echo",
  version: "1.0.0",
  status: "active",
  scopes: ["posts:read"],
  events: ["mention"],
  egress: [],
  enabled: false,
  bot_user_id: null,
  settings_schema: { key: { type: "secret", label: "API key" } },
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => vi.clearAllMocks());

describe("InstallUrlDialog", () => {
  it("gates submit on every scope being ticked, then resends them", async () => {
    client.apiPost
      .mockRejectedValueOnce(
        new ApiError(422, "scopes_not_approved", "no", {
          scopes: ["posts:read", "comments:write"],
          events: ["mention"],
          egress: ["api.example.com"],
        }),
      )
      .mockResolvedValueOnce(plugin);
    wrap(<InstallUrlDialog open onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Manifest URL"), {
      target: { value: "https://x/m.json" },
    });
    fireEvent.change(screen.getByLabelText("Endpoint URL"), {
      target: { value: "https://x/" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByText("api.example.com");
    expect(client.apiPost.mock.calls[0][1]).toMatchObject({
      source: "url",
      approved_scopes: [],
    });
    const go = screen.getByRole("button", { name: "Approve and install" });
    expect(go).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Read posts"));
    expect(go).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Create comments"));
    expect(go).toBeEnabled();
    fireEvent.click(go);
    await waitFor(() => expect(client.apiPost).toHaveBeenCalledTimes(2));
    expect(client.apiPost.mock.calls[1][1].approved_scopes).toEqual([
      "posts:read",
      "comments:write",
    ]);
  });
});

describe("UninstallDialog", () => {
  it("defaults delete_content to false and sends true when ticked", () => {
    const onConfirm = vi.fn();
    render(
      <UninstallDialog
        open
        name="Echo"
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Uninstall" }));
    expect(onConfirm).toHaveBeenLastCalledWith(false);
    fireEvent.click(
      screen.getByLabelText("Also delete all its posts and comments"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Uninstall" }));
    expect(onConfirm).toHaveBeenLastCalledWith(true);
  });
});

describe("CredentialsDialog", () => {
  it("shows the secrets with the one-time warning", () => {
    render(
      <CredentialsDialog
        credentials={{
          token: "tok-123",
          webhook_secret: "whs-456",
          community_id: "c1",
        }}
        onClose={vi.fn()}
      />,
    );
    expect(
      screen.getByText("Copy these now. They will not be shown again."),
    ).toBeInTheDocument();
    expect(screen.getByText("tok-123")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy token" }),
    ).toBeInTheDocument();
  });
});

describe("InstalledTab", () => {
  it("lists plugins", async () => {
    client.apiGet.mockResolvedValue([plugin]);
    wrap(<InstalledTab />);
    expect(await screen.findByText("Echo")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/app/admin/plugins/echo",
    );
  });
});

describe("PluginDetail", () => {
  it("enables in own community and shows credentials once", async () => {
    client.apiGet.mockImplementation(async (u: string) =>
      u.endsWith("/settings") ? { key: { set: false } } : [plugin],
    );
    client.apiPatch.mockResolvedValue({
      plugin_id: "echo",
      enabled: true,
      bot_user_id: "b",
      settings: {},
      credentials: { token: "tok-9", webhook_secret: "s", community_id: "c1" },
    });
    wrap(<PluginDetail pluginId="echo" />);
    fireEvent.click(
      await screen.findByRole("switch", { name: "Enabled in this community" }),
    );
    expect(await screen.findByText("tok-9")).toBeInTheDocument();
    expect(client.apiPatch).toHaveBeenCalledWith(
      "/api/v1/plugins/echo/communities/c1",
      { enabled: true },
    );
  });
});
