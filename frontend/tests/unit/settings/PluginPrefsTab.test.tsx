/**
 * @file tests/unit/settings/PluginPrefsTab.test.tsx
 * @brief Member plugin prefs load and save.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  get: vi.fn(async () => ({ tone: "mild" })),
  put: vi.fn(async (_id: string, v: unknown) => v),
}));
vi.mock("@/hooks/usePluginUi", () => ({
  usePluginUi: () => ({
    data: [
      {
        plugin_id: "sassy",
        name: "Sassybot",
        composer_flags: {},
        user_prefs: {
          tone: { type: "string", label: "Tone" },
        },
      },
      {
        plugin_id: "none",
        name: "NoPrefs",
        composer_flags: {},
        user_prefs: {},
      },
    ],
  }),
}));
vi.mock("@/lib/api/plugins", () => ({
  getPluginPrefs: api.get,
  putPluginPrefs: api.put,
}));

import { PluginPrefsTab } from "@/components/settings/PluginPrefsTab";

describe("PluginPrefsTab", () => {
  it("saves edited prefs", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <PluginPrefsTab />
      </QueryClientProvider>,
    );
    expect(screen.queryByText("NoPrefs")).toBeNull();
    const input = await screen.findByDisplayValue("mild");
    const user = userEvent.setup();
    await user.clear(input);
    await user.type(input, "spicy");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith("sassy", { tone: "spicy" }),
    );
  });
});
