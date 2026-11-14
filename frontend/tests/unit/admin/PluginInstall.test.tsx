/**
 * @file tests/unit/admin/PluginInstall.test.tsx
 * @brief Two-step plugin install dialog: staging, permissions diff, confirm.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PluginInstallDialog } from "@/components/admin/PluginInstallDialog";
import { apiPost } from "@/lib/api/client";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
}));

const review = {
  plugin_id: "trivia",
  manifest: {
    id: "trivia",
    name: "Trivia",
    version: "1.2.0",
    author: "Nexara",
    description: "Weekly trivia",
    permissions: ["db_read", "db_write"],
    settings: {},
  },
  permissions_requested: ["db_read", "db_write"],
  permissions_previously_granted: ["db_read"],
  new_permissions: ["db_write"],
  removed_permissions: [],
};

function setup(onClose = vi.fn()) {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <PluginInstallDialog open onClose={onClose} />
    </QueryClientProvider>,
  );
  return onClose;
}

async function toStep2() {
  await userEvent.type(screen.getByLabelText("Plugin ID"), "trivia");
  await userEvent.click(screen.getByRole("button", { name: /review/i }));
  await screen.findByText(/step 2 of 2/i);
}

describe("PluginInstallDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiPost).mockResolvedValue(review);
  });

  it("starts on step 1 with a labelled plugin id field", () => {
    setup();
    expect(screen.getByText(/step 1 of 2/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Plugin ID")).toBeInTheDocument();
  });

  it("stages the install and shows step 2", async () => {
    setup();
    await toStep2();
    expect(apiPost).toHaveBeenCalledWith(
      "/api/v1/admin/plugins/install-request",
      { plugin_id: "trivia" },
    );
    expect(screen.getByText("Weekly trivia")).toBeInTheDocument();
  });

  it("describes permissions and highlights new ones", async () => {
    setup();
    await toStep2();
    expect(screen.getByText("db_read")).toBeInTheDocument();
    expect(screen.getByText("db_write")).toBeInTheDocument();
    expect(screen.getAllByText("New")).toHaveLength(1);
    expect(screen.getByTestId("perm-db_write")).toHaveAttribute(
      "data-sensitive",
      "true",
    );
    expect(screen.getByTestId("perm-db_read")).not.toHaveAttribute(
      "data-sensitive",
    );
  });

  it("confirm calls the confirm endpoint and shows the key once", async () => {
    setup();
    await toStep2();
    vi.mocked(apiPost).mockResolvedValueOnce({
      id: "trivia",
      api_key: "nxp_secret",
    });
    await userEvent.click(screen.getByRole("button", { name: /^install$/i }));
    await waitFor(() =>
      expect(apiPost).toHaveBeenLastCalledWith(
        "/api/v1/admin/plugins/install-confirm",
        { plugin_id: "trivia" },
      ),
    );
    expect(await screen.findByText("nxp_secret")).toBeInTheDocument();
  });

  it("cancel closes without confirming", async () => {
    const onClose = setup();
    await toStep2();
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
    expect(apiPost).toHaveBeenCalledTimes(1);
  });
});
