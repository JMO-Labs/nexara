/**
 * @file tests/unit/admin/PluginSettings.test.tsx
 * @brief Dynamic plugin settings form: validation, secret masking, save.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PluginSettingsForm } from "@/components/admin/PluginSettingsForm";
import { apiPut } from "@/lib/api/client";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
}));

// jsdom lacks ResizeObserver (used by Radix Switch via useSize).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const schema = {
  title: { type: "string", label: "Title", required: true },
  rounds: { type: "integer", label: "Rounds", required: false },
  ratio: { type: "number", label: "Ratio", required: false },
  enabled: { type: "boolean", label: "Live mode", required: false },
  token: { type: "string", label: "Api Token", secret: true },
} as const;

function setup(values: Record<string, unknown> = {}) {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={qc}>
      <PluginSettingsForm
        pluginId="trivia"
        schema={schema as never}
        values={{ title: "Quiz", rounds: 5, token: "••••", ...values }}
      />
    </QueryClientProvider>,
  );
}

describe("PluginSettingsForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiPut).mockResolvedValue({ settings: {} });
  });

  it("renders a labelled field per setting type", () => {
    setup();
    expect(screen.getByLabelText("Title")).toHaveValue("Quiz");
    expect(screen.getByLabelText("Rounds")).toHaveAttribute("type", "number");
    expect(screen.getByRole("switch", { name: "Live mode" })).toBeVisible();
  });

  it("masks secret fields and toggles with the eye button", async () => {
    setup();
    const input = screen.getByLabelText("Api Token");
    expect(input).toHaveAttribute("type", "password");
    await userEvent.click(
      screen.getByRole("button", { name: /show api token/i }),
    );
    expect(input).toHaveAttribute("type", "text");
    await userEvent.click(
      screen.getByRole("button", { name: /hide api token/i }),
    );
    expect(input).toHaveAttribute("type", "password");
  });

  it("validates required fields and does not call the API", async () => {
    setup();
    await userEvent.clear(screen.getByLabelText("Title"));
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(await screen.findByText("Title is required")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(apiPut).not.toHaveBeenCalled();
  });

  it("validates integers", async () => {
    setup();
    const r = screen.getByLabelText("Rounds");
    await userEvent.clear(r);
    await userEvent.type(r, "2.5");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(
      await screen.findByText("Rounds must be a whole number"),
    ).toBeInTheDocument();
    expect(apiPut).not.toHaveBeenCalled();
  });

  it("saves typed values and omits untouched secrets", async () => {
    setup();
    await userEvent.type(screen.getByLabelText("Title"), "!");
    await userEvent.click(screen.getByRole("switch", { name: "Live mode" }));
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() =>
      expect(apiPut).toHaveBeenCalledWith("/api/v1/plugins/trivia/settings", {
        settings: { title: "Quiz!", rounds: 5, enabled: true },
      }),
    );
  });
});
