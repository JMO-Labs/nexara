/**
 * @file tests/unit/help/help.test.tsx
 * @brief HelpButton, KeyboardShortcutsModal and WelcomeModal behavior.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HelpButton } from "@/components/help/HelpButton";
import { KeyboardShortcutsModal } from "@/components/help/KeyboardShortcutsModal";
import { WelcomeModal } from "@/components/onboarding/WelcomeModal";
import { useModals } from "@/stores/modals";
import { useSession } from "@/stores/session";

const complete = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/api/users", () => ({
  completeOnboarding: () => complete(),
}));

beforeEach(() => {
  complete.mockClear();
  useModals.setState({ keyboardShortcutsOpen: false });
  useSession.setState({ user: null } as never);
});

describe("HelpButton", () => {
  it("opens menu and triggers shortcuts modal", async () => {
    render(<HelpButton />);
    await userEvent.click(screen.getByRole("button", { name: "Help menu" }));
    expect(
      screen.getByRole("menuitem", { name: "Documentation" }),
    ).toHaveAttribute("href", "/docs");
    expect(
      screen.getByRole("menuitem", { name: "Contact support" }),
    ).toHaveAttribute("href", "/contact");
    await userEvent.click(
      screen.getByRole("menuitem", { name: "Keyboard shortcuts" }),
    );
    expect(useModals.getState().keyboardShortcutsOpen).toBe(true);
  });
});

describe("KeyboardShortcutsModal", () => {
  it("renders sections when open", () => {
    useModals.setState({ keyboardShortcutsOpen: true });
    render(<KeyboardShortcutsModal />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Navigation")).toBeInTheDocument();
    expect(screen.getByText("Ctrl+K")).toBeInTheDocument();
    expect(screen.getByText("Next image")).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    render(<KeyboardShortcutsModal />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("WelcomeModal", () => {
  it("hidden without a fresh user", () => {
    render(<WelcomeModal />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("skip marks onboarding complete", async () => {
    useSession.setState({
      user: { id: "u", tour_completed_at: null },
    } as never);
    render(<WelcomeModal />);
    expect(screen.getByText("Edit profile")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    expect(complete).toHaveBeenCalledOnce();
  });

  it("take tour closes without completing", async () => {
    useSession.setState({
      user: { id: "u", tour_completed_at: null },
    } as never);
    render(<WelcomeModal />);
    await userEvent.click(screen.getByRole("button", { name: "Take tour" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(complete).not.toHaveBeenCalled();
  });
});
