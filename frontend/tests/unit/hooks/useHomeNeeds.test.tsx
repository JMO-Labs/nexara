/**
 * @file tests/unit/hooks/useHomeNeeds.test.tsx
 * @brief useHomeNeeds: calls getHomeNeeds once and returns data.
 */
import { waitFor } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/home", () => ({ getHomeNeeds: vi.fn() }));

import { useHomeNeeds } from "@/hooks/useHomeNeeds";
import * as api from "@/lib/api/home";

describe("useHomeNeeds", () => {
  it("fetches once and returns data", async () => {
    vi.mocked(api.getHomeNeeds).mockResolvedValue({ items: [] } as never);
    const { result } = renderHookWithProviders(() => useHomeNeeds());
    await waitFor(() => expect(result.current.data).toEqual({ items: [] }));
    expect(api.getHomeNeeds).toHaveBeenCalledTimes(1);
  });
});
