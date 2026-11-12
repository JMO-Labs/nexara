/**
 * @file tests/unit/engagement/NudgeButton.test.tsx
 * @brief NudgeButton: send, success toast, 429 cooldown, timer label.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  NudgeButton,
  formatCooldown,
} from "@/components/engagement/NudgeButton";
import { ApiError } from "@/lib/api/errors";
import { useToasts } from "@/stores/toasts";
import * as nudgesApi from "@/lib/api/nudges";

vi.mock("@/lib/api/nudges");

describe("formatCooldown", () => {
  it("formats elapsed time", () => {
    expect(formatCooldown(30_000)).toBe("Nudged just now");
    expect(formatCooldown(4 * 3600_000 + 60_000)).toBe("Nudged 4h ago");
    expect(formatCooldown(25 * 60_000)).toBe("Nudged 25m ago");
  });
});

describe("NudgeButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useToasts.getState().clear();
  });

  it("sends nudge, toasts, and disables", async () => {
    vi.mocked(nudgesApi.sendNudge).mockResolvedValue({} as never);
    render(<NudgeButton userId="u1" />);
    await userEvent.click(screen.getByRole("button", { name: "Nudge" }));
    await waitFor(() =>
      expect(nudgesApi.sendNudge).toHaveBeenCalledWith("u1", undefined),
    );
    expect(useToasts.getState().items[0].message).toBe("Nudge sent!");
    const btn = await screen.findByRole("button", { name: /Nudged/ });
    expect(btn).toBeDisabled();
  });

  it("on 429 shows toast and cooldown", async () => {
    vi.mocked(nudgesApi.sendNudge).mockRejectedValue(
      new ApiError(429, "RATE_LIMITED", "slow"),
    );
    render(<NudgeButton userId="u1" />);
    await userEvent.click(screen.getByRole("button", { name: "Nudge" }));
    await waitFor(() =>
      expect(useToasts.getState().items[0].message).toBe(
        "You've already nudged this person in the last 24 hours",
      ),
    );
    expect(screen.getByRole("button", { name: /Nudged/ })).toBeDisabled();
  });

  it("on other error shows error toast", async () => {
    vi.mocked(nudgesApi.sendNudge).mockRejectedValue(
      new ApiError(403, "FORBIDDEN", "Blocked"),
    );
    render(<NudgeButton userId="u1" />);
    await userEvent.click(screen.getByRole("button", { name: "Nudge" }));
    await waitFor(() =>
      expect(useToasts.getState().items[0].message).toBe("Blocked"),
    );
    expect(screen.getByRole("button", { name: "Nudge" })).toBeEnabled();
  });

  it("starts disabled from stored recent nudge, enabled after 24h", () => {
    localStorage.setItem("nudge:u1", String(Date.now() - 4 * 3600_000));
    const { unmount } = render(<NudgeButton userId="u1" />);
    expect(
      screen.getByRole("button", { name: "Nudged 4h ago" }),
    ).toBeDisabled();
    unmount();
    localStorage.setItem("nudge:u1", String(Date.now() - 25 * 3600_000));
    render(<NudgeButton userId="u1" />);
    expect(screen.getByRole("button", { name: "Nudge" })).toBeEnabled();
  });
});
