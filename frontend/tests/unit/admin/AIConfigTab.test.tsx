/**
 * @file tests/unit/admin/AIConfigTab.test.tsx
 * @brief Tests for AIConfigTab (provider, Sassybot settings, budget & metrics).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import * as hooks from "@/hooks/useAdminAI";
import { AIConfigTab } from "@/components/admin/AIConfigTab";

vi.mock("@/hooks/useAdminAI");

const config = {
  provider: "ollama",
  sassybot_enabled: true,
  sass_level: 2,
  probability: 20,
  invoke_only: false,
  opt_out_count: 3,
};
const metrics = {
  daily_usage_cents: 85,
  daily_budget_cents: 100,
  last_7_days: Array.from({ length: 7 }, (_, i) => ({
    date: `2026-11-0${i + 1}`,
    cents: i * 10,
  })),
  breakdown: [
    { feature: "ocr", calls: 4, cents: 40 },
    { feature: "suggestion", calls: 0, cents: 0 },
    { feature: "sassybot", calls: 9, cents: 45 },
  ],
};
const update = { mutate: vi.fn(), isPending: false, isSuccess: false };
const test = { mutate: vi.fn(), isPending: false, data: undefined as any };

function setup(overrides: Record<string, unknown> = {}) {
  vi.mocked(hooks.useAdminAIConfig).mockReturnValue({
    data: config,
    isLoading: false,
    ...overrides,
  } as any);
  vi.mocked(hooks.useAdminAIMetrics).mockReturnValue({
    data: metrics,
    isLoading: false,
  } as any);
  vi.mocked(hooks.useUpdateAdminAIConfig).mockReturnValue(update as any);
  vi.mocked(hooks.useTestAIConnection).mockReturnValue(test as any);
}

describe("AIConfigTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    test.data = undefined;
  });

  it("shows loading state", () => {
    setup({ data: undefined, isLoading: true });
    render(<AIConfigTab />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders provider radios read-only with selected provider", () => {
    setup();
    render(<AIConfigTab />);
    expect(screen.getByRole("radio", { name: "Ollama" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "OpenAI" })).not.toBeChecked();
    expect(screen.getByText(/Ollama runs locally/)).toBeInTheDocument();
  });

  it("test connection triggers mutation and shows result", () => {
    setup();
    test.data = { success: true, message: "Connection successful" };
    render(<AIConfigTab />);
    fireEvent.click(screen.getByRole("button", { name: /test connection/i }));
    expect(test.mutate).toHaveBeenCalled();
    expect(screen.getByText("Connection successful")).toBeInTheDocument();
  });

  it("renders labelled sassybot controls and opt-out count", () => {
    setup();
    render(<AIConfigTab />);
    expect(
      screen.getByRole("switch", { name: /enable sassybot/i }),
    ).toBeChecked();
    expect(screen.getByLabelText(/sass level/i)).toHaveValue("2");
    expect(screen.getByLabelText(/probability/i)).toHaveValue("20");
    expect(screen.getByText("20%")).toBeInTheDocument();
    expect(screen.getByText(/3 users have opted out/)).toBeInTheDocument();
  });

  it("saves changed settings", () => {
    setup();
    render(<AIConfigTab />);
    fireEvent.change(screen.getByLabelText(/sass level/i), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("switch", { name: /invoke-only/i }));
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(update.mutate).toHaveBeenCalledWith({
      sassybot_enabled: true,
      sass_level: 3,
      probability: 20,
      invoke_only: true,
    });
  });

  it("renders budget text, progress, chart and table, with 80% warning", () => {
    setup();
    render(<AIConfigTab />);
    expect(
      screen.getByText("Daily Budget: $0.85 / $1.00 spent (85% used)"),
    ).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "85",
    );
    expect(
      screen.getByRole("img", { name: /last 7 days/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/80%/);
    const row = screen.getByRole("row", { name: /sassybot/i });
    expect(row).toHaveTextContent("9");
    expect(row).toHaveTextContent("$0.45");
  });
});
