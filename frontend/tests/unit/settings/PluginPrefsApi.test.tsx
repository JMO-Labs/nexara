/**
 * @file tests/unit/settings/PluginPrefsApi.test.tsx
 * @brief Real usePluginUi + plugins API: endpoints, PUT body shape, load error retry.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.unmock("@/hooks/usePluginUi");
const c = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(async (_p: string, b: unknown) => b),
}));
vi.mock("@/lib/api/client", () => ({
  apiGet: c.apiGet,
  apiPut: c.apiPut,
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  seg: (s: string) => encodeURIComponent(s),
}));

import { PluginPrefsTab } from "@/components/settings/PluginPrefsTab";

const ui = [
  {
    plugin_id: "sassy",
    name: "Sassybot",
    composer_flags: {},
    user_prefs: { tone: { type: "string", label: "Tone" } },
  },
];

function mount() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <PluginPrefsTab />
    </QueryClientProvider>,
  );
}

describe("plugin prefs via real hook and API", () => {
  it("loads from /plugins/ui and PUTs {values}", async () => {
    c.apiGet.mockImplementation(async (path: string) =>
      path === "/api/v1/plugins/ui" ? ui : { tone: "mild" },
    );
    mount();
    const input = await screen.findByDisplayValue("mild");
    const user = userEvent.setup();
    await user.clear(input);
    await user.type(input, "hot");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(c.apiPut).toHaveBeenCalledWith("/api/v1/me/plugin-prefs/sassy", {
        values: { tone: "hot" },
      }),
    );
  });

  it("shows an error with retry when prefs fail to load", async () => {
    let fail = true;
    c.apiGet.mockImplementation(async (path: string) => {
      if (path === "/api/v1/plugins/ui") return ui;
      if (fail) throw new Error("boom");
      return { tone: "ok" };
    });
    mount();
    const retry = await screen.findByRole("button", { name: "Retry" });
    fail = false;
    await userEvent.setup().click(retry);
    expect(await screen.findByDisplayValue("ok")).toBeInTheDocument();
  });
});
