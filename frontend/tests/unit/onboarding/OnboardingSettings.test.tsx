/**
 * @file tests/unit/onboarding/OnboardingSettings.test.tsx
 * @brief Admin switches save the required-steps list.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const api = vi.hoisted(() => ({
  getRequiredSteps: vi.fn().mockResolvedValue({ required: ["profile"] }),
  putRequiredSteps: vi
    .fn()
    .mockResolvedValue({ required: ["profile", "birthday"] }),
}));
vi.mock("@/lib/api/onboarding", () => api);

import { OnboardingSettings } from "@/components/admin/OnboardingSettings";

describe("OnboardingSettings", () => {
  it("toggling birthday saves profile + birthday", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <OnboardingSettings />
      </QueryClientProvider>,
    );
    const sw = await screen.findByRole("switch", { name: "Require birthday" });
    await waitFor(() => expect(sw).not.toBeDisabled());
    fireEvent.click(sw);
    await waitFor(() =>
      expect(api.putRequiredSteps).toHaveBeenCalledWith([
        "profile",
        "birthday",
      ]),
    );
  });
});
