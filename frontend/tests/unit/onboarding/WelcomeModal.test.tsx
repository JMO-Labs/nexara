/**
 * @file tests/unit/onboarding/WelcomeModal.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WelcomeModal } from "@/components/onboarding/WelcomeModal";
import { useSession } from "@/stores/session";

const complete = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/api/users", () => ({ completeOnboarding: () => complete() }));

describe("WelcomeModal", () => {
  beforeEach(() => {
    complete.mockClear();
    useSession.setState({
      user: { id: "u1", tour_completed_at: null },
    } as never);
  });

  it("has an accessible title via aria-labelledby", () => {
    render(<WelcomeModal />);
    const dlg = screen.getByRole("dialog");
    const id = dlg.getAttribute("aria-labelledby");
    expect(id).toBeTruthy();
    expect(document.getElementById(id as string)).toHaveTextContent(
      "Welcome to the community!",
    );
  });

  it("closes on Escape and marks onboarding done", async () => {
    render(<WelcomeModal />);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(complete).toHaveBeenCalledTimes(1);
    expect(useSession.getState().user?.tour_completed_at).toBeTruthy();
  });

  it("Skip for now marks onboarding done", async () => {
    render(<WelcomeModal />);
    await userEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    expect(complete).toHaveBeenCalledTimes(1);
  });
});
