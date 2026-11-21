/**
 * @file tests/unit/hooks/useHomePeople.test.tsx
 * @brief useHomePeople: calls getHomePeople once and returns data.
 */
import { waitFor } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/home", () => ({ getHomePeople: vi.fn() }));

import { useHomePeople } from "@/hooks/useHomePeople";
import * as api from "@/lib/api/home";

describe("useHomePeople", () => {
  it("fetches once and returns data", async () => {
    vi.mocked(api.getHomePeople).mockResolvedValue({ items: [] } as never);
    const { result } = renderHookWithProviders(() => useHomePeople());
    await waitFor(() => expect(result.current.data).toEqual({ items: [] }));
    expect(api.getHomePeople).toHaveBeenCalledTimes(1);
  });
});
