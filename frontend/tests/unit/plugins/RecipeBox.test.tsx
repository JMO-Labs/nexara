/**
 * @file RecipeBox.test.tsx
 * @brief Tests for the example recipe box plugin UI.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

vi.mock("@/lib/api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
  seg: (s: string) => encodeURIComponent(s),
}));
vi.mock("@/lib/api/users", () => ({
  getMe: vi.fn().mockResolvedValue({ id: "u1" }),
}));
vi.mock("@/lib/api/media", () => ({ uploadFile: vi.fn() }));

import { apiGet, apiPost } from "@/lib/api/client";
import { useToasts } from "@/stores/toasts";
import { PluginRegistry } from "@/lib/plugins/plugin-loader";
import { registerPlugin } from "@/plugins/example-recipe-box";
import RecipeBoxWidget from "@/plugins/example-recipe-box/components/RecipeBoxWidget";
import RecipeForm, {
  validateRecipe,
} from "@/plugins/example-recipe-box/components/RecipeForm";

const recipe = {
  id: "r1",
  owner_id: "u1",
  name: "Pancakes",
  ingredients: [{ name: "flour", qty: 2, unit: "cup" }],
  steps: ["mix"],
  tags: ["breakfast"],
  image_url: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const wrap = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {children}
  </QueryClientProvider>
);
const props = {
  pluginId: "example-recipe-box",
  pluginManifest: {
    id: "example-recipe-box",
    name: "x",
    version: "1",
    is_enabled: true,
    description: "",
  },
};

describe("RecipeBox plugin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    vi.mocked(apiGet).mockResolvedValue({ items: [recipe], total: 1 });
  });

  it("registers the widget in sidebar-widget slot", () => {
    PluginRegistry.getInstance().reset();
    registerPlugin(PluginRegistry.getInstance());
    expect(
      PluginRegistry.getInstance().getSlotComponents("sidebar-widget"),
    ).toHaveLength(1);
  });

  it("widget renders recipe of the day with summary", async () => {
    render(<RecipeBoxWidget {...props} />, { wrapper: wrap });
    expect(await screen.findByText("Pancakes")).toBeInTheDocument();
    expect(screen.getByText(/1 ingredients?, 1 steps?/)).toBeInTheDocument();
  });

  it("opens modal on click", async () => {
    render(<RecipeBoxWidget {...props} />, { wrapper: wrap });
    await userEvent.click(
      await screen.findByRole("button", { name: /browse recipes/i }),
    );
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("validates form", () => {
    expect(validateRecipe({ name: "", ingredients: [], steps: [] })).toEqual(
      expect.objectContaining({ name: expect.any(String) }),
    );
    expect(
      validateRecipe({
        name: "a",
        ingredients: [{ name: "x", qty: null, unit: "" }],
        steps: ["s"],
      }),
    ).toEqual({});
  });

  it("form blocks submit when invalid and calls hook when valid", async () => {
    vi.mocked(apiPost).mockResolvedValue(recipe);
    const onDone = vi.fn();
    render(<RecipeForm onDone={onDone} onCancel={() => {}} />, {
      wrapper: wrap,
    });
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(apiPost).not.toHaveBeenCalled();
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/^name/i), "Soup");
    await userEvent.type(screen.getByLabelText(/ingredient 1 name/i), "water");
    await userEvent.type(screen.getByLabelText(/^steps/i), "boil");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() => expect(apiPost).toHaveBeenCalled());
    expect(vi.mocked(apiPost).mock.calls[0][0]).toBe(
      "/api/v1/plugins/example-recipe-box/recipes",
    );
    expect(vi.mocked(apiPost).mock.calls[0][1]).toMatchObject({
      name: "Soup",
      steps: ["boil"],
    });
  });

  it("shows error toast when API fails", async () => {
    vi.mocked(apiPost).mockRejectedValue(new Error("nope"));
    render(<RecipeForm onDone={() => {}} onCancel={() => {}} />, {
      wrapper: wrap,
    });
    await userEvent.type(screen.getByLabelText(/^name/i), "Soup");
    await userEvent.type(screen.getByLabelText(/ingredient 1 name/i), "water");
    await userEvent.type(screen.getByLabelText(/^steps/i), "boil");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() =>
      expect(
        useToasts.getState().items.some((t) => t.variant === "danger"),
      ).toBe(true),
    );
  });
});
