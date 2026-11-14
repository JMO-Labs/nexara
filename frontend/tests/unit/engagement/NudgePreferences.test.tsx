/**
 * @file tests/unit/engagement/NudgePreferences.test.tsx
 * @brief NudgePreferences toggles persist via useUpdateSettings.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NudgePreferences } from "@/components/settings/NudgePreferences";
import * as hooks from "@/hooks/useSettings";

vi.mock("@/hooks/useSettings");

describe("NudgePreferences", () => {
  const mutate = vi.fn();
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(hooks.useUserSettings).mockReturnValue({
      data: { receive_nudges: true, receive_gentle_nudges: false },
      isLoading: false,
    } as never);
    vi.mocked(hooks.useUpdateSettings).mockReturnValue({ mutate } as never);
  });

  it("renders toggles with state and descriptions", () => {
    render(<NudgePreferences />);
    expect(
      screen.getByRole("switch", { name: "Receive nudges" }),
    ).toBeChecked();
    expect(
      screen.getByRole("switch", { name: "Receive gentle reminders" }),
    ).not.toBeChecked();
    expect(
      screen.getByText("Let others nudge you as a friendly reminder"),
    ).toBeInTheDocument();
  });

  it("saves changes", async () => {
    render(<NudgePreferences />);
    await userEvent.click(
      screen.getByRole("switch", { name: "Receive nudges" }),
    );
    expect(mutate).toHaveBeenCalledWith({ receive_nudges: false });
    await userEvent.click(
      screen.getByRole("switch", { name: "Receive gentle reminders" }),
    );
    expect(mutate).toHaveBeenCalledWith({ receive_gentle_nudges: true });
  });
});
