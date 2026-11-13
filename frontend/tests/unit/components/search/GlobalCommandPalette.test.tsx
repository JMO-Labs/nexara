/**
 * @file tests/unit/components/search/GlobalCommandPalette.test.tsx
 * @brief Ctrl+K toggles the palette store flag.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/hooks/useSearch", () => ({
  useGlobalSearch: () => ({ data: undefined, isLoading: false }),
}));

import { GlobalCommandPalette } from "@/components/search/GlobalCommandPalette";
import { useUI } from "@/stores/ui";

describe("GlobalCommandPalette", () => {
  beforeEach(() => useUI.setState({ commandPaletteOpen: false }));

  it("opens on Ctrl+K", async () => {
    render(<GlobalCommandPalette />);
    expect(useUI.getState().commandPaletteOpen).toBe(false);
    await userEvent.keyboard("{Control>}k{/Control}");
    expect(useUI.getState().commandPaletteOpen).toBe(true);
  });
});
