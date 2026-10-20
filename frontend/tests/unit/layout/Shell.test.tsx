/**
 * @file tests/unit/layout/Shell.test.tsx
 * @brief Shell landmarks, safe-area padding, skip link, chat dock wrapper.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app",
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/hooks/useSession", () => ({ useSessionBootstrap: vi.fn() }));
const { stub } = vi.hoisted(() => ({
  stub: (name: string, label?: string) => ({
    [name]: () => (label ? <div data-testid={label} /> : null),
  }),
}));
vi.mock("@/components/layout/TopBar", () => stub("TopBar"));
vi.mock("@/components/layout/ModalRoot", () => stub("ModalRoot"));
vi.mock("@/components/help/KeyboardShortcutsModal", () =>
  stub("KeyboardShortcutsModal"),
);
vi.mock("@/components/help/HelpButton", () => stub("HelpButton"));
vi.mock("@/components/onboarding/OnboardingTour", () => stub("OnboardingTour"));
vi.mock("@/components/onboarding/WelcomeModal", () => stub("WelcomeModal"));
vi.mock("@/components/home/RightRail", () => stub("RightRail", "rail"));
vi.mock("@/components/ui/ConfirmDialog", () => stub("ConfirmDialog"));
vi.mock("@/components/chat/FloatingChatDock", () =>
  stub("FloatingChatDock", "dock"),
);

import { Shell } from "@/components/layout/Shell";
import { useSession } from "@/stores/session";

function setup() {
  useSession.setState({
    user: { is_admin: false, role: "member" } as never,
    status: "authenticated",
  });
  return render(
    <Shell>
      <p>content</p>
    </Shell>,
  );
}

describe("Shell", () => {
  it("renders both navigations", () => {
    setup();
    expect(
      screen.getByRole("navigation", { name: "Main" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Primary" }),
    ).toBeInTheDocument();
  });

  it("pads main for the tab bar and safe area", () => {
    setup();
    expect(screen.getByRole("main").className).toContain(
      "env(safe-area-inset-bottom)",
    );
  });

  it("makes the skip link the first tab stop", async () => {
    setup();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Skip to content" })).toHaveFocus();
  });

  it("hides the chat dock on phones", () => {
    setup();
    expect(screen.getByTestId("dock").parentElement).toHaveClass(
      "hidden",
      "md:block",
    );
  });

  it("does not mount the right rail", () => {
    setup();
    expect(screen.queryByTestId("rail")).not.toBeInTheDocument();
  });
});
