/**
 * @file tests/unit/admin/FeaturesTab.test.tsx
 * @brief Features tab: toggling a switch PUTs only that key.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as api from "@/lib/api/features";
import { FeaturesTab } from "@/components/admin/FeaturesTab";

vi.mock("@/lib/api/features", async (orig) => ({
  ...(await orig<typeof api>()),
  getFeatures: vi.fn(),
  putFeatures: vi.fn(),
}));

const flags = Object.fromEntries(
  api.FEATURE_KEYS.map((k) => [k, k !== "reply_by_email"]),
) as api.Features;

describe("FeaturesTab", () => {
  it("sends a single-key patch", async () => {
    vi.mocked(api.getFeatures).mockResolvedValue(flags);
    vi.mocked(api.putFeatures).mockResolvedValue({ ...flags, recipes: false });
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <FeaturesTab />
      </QueryClientProvider>,
    );
    fireEvent.click(await screen.findByRole("switch", { name: "Recipes" }));
    await waitFor(() =>
      expect(api.putFeatures).toHaveBeenCalledWith({ recipes: false }),
    );
  });
});
