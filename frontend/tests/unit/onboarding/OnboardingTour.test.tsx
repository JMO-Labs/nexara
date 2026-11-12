/**
 * @file tests/unit/onboarding/OnboardingTour.test.tsx
 * @brief Joyride is faked; asserts the v3 prop contract (onEvent, locale, buttons).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OnboardingTour } from "@/components/onboarding/OnboardingTour";
import { useSession } from "@/stores/session";

const complete = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/api/users", () => ({ completeOnboarding: () => complete() }));

/* eslint-disable @typescript-eslint/no-explicit-any */
vi.mock("next/dynamic", () => ({
  default: () =>
    function FakeJoyride(p: any) {
      const [i, setI] = useState(0);
      const n = p.steps.length;
      const loc = p.locale;
      const btns: string[] = p.options.buttons;
      const ev = (status: string, action: string) =>
        p.onEvent({ status, action, index: i, type: "tour:end" });
      return (
        <div role="dialog" aria-label="tour">
          {btns.includes("back") && (
            <button disabled={i === 0} onClick={() => setI(i - 1)}>
              {loc.back}
            </button>
          )}
          {btns.includes("skip") && (
            <button onClick={() => ev("skipped", "skip")}>{loc.skip}</button>
          )}
          <button
            onClick={() => (i === n - 1 ? ev("finished", "next") : setI(i + 1))}
          >
            {i === n - 1
              ? loc.last
              : loc.nextWithProgress
                  .replace("{current}", String(i + 1))
                  .replace("{total}", String(n))}
          </button>
          <span>{`Step ${i + 1} of ${n}`}</span>
        </div>
      );
    },
}));

describe("OnboardingTour", () => {
  beforeEach(() => {
    complete.mockClear();
    useSession.setState({
      user: { id: "u1", is_admin: false, tour_completed_at: null },
    } as never);
  });

  it("shows Back, Next, Skip and step progress", () => {
    render(<OnboardingTour />);
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Next/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Skip" })).toBeInTheDocument();
    expect(screen.getByText(/^Step 1 of \d+$/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Step 1 of \d+/ }),
    ).toBeInTheDocument();
  });

  it("is operable by keyboard only", async () => {
    render(<OnboardingTour />);
    await userEvent.tab(); // Back is disabled, so first stop is Skip
    expect(screen.getByRole("button", { name: "Skip" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: /^Next/ })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByText(/^Step 2 of/)).toBeInTheDocument();
  });

  it("Skip marks onboarding done and unmounts", async () => {
    render(<OnboardingTour />);
    await userEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(complete).toHaveBeenCalledTimes(1);
    expect(useSession.getState().user?.tour_completed_at).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("finishing marks onboarding done", async () => {
    render(<OnboardingTour />);
    for (let k = 0; k < 20 && screen.queryByRole("dialog"); k++) {
      await userEvent.click(
        screen.getByRole("button", { name: /^(Next|Finish)/ }),
      );
    }
    expect(complete).toHaveBeenCalledTimes(1);
  });

  it("renders nothing once completed", () => {
    useSession.setState({
      user: { id: "u1", tour_completed_at: "2026-01-01" },
    } as never);
    render(<OnboardingTour />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
