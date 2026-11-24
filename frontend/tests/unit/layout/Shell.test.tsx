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
vi.mock("@/components/layout/GraceBanner", () => stub("GraceBanner"));
vi.mock("@/components/layout/AppBackdrop", () =>
  stub("AppBackdrop", "backdrop"),
);
vi.mock("@/components/layout/BottomTabBar", async (orig) => ({
  ...(await orig<typeof import("@/components/layout/BottomTabBar")>()),
  BottomTabBar: () => <nav aria-label="Primary" />,
}));
const settings = vi.hoisted(() => ({ data: undefined as unknown }));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: settings.data }),
}));
vi.mock("@/components/layout/BrandingStyle", () => stub("BrandingStyle"));
vi.mock("@/components/layout/SimpleModeSync", () => stub("SimpleModeSync"));
vi.mock("@/components/layout/ModalRoot", () => stub("ModalRoot"));
vi.mock("@/components/help/KeyboardShortcutsModal", () =>
  stub("KeyboardShortcutsModal"),
);
vi.mock("@/components/onboarding/OnboardingTour", () => stub("OnboardingTour"));
vi.mock("@/components/onboarding/WelcomeModal", () => stub("WelcomeModal"));
vi.mock("@/components/ui/ConfirmDialog", () => stub("ConfirmDialog"));
vi.mock("@/components/chat/FloatingChatDock", () =>
  stub("FloatingChatDock", "dock"),
);

import { Shell } from "@/components/layout/Shell";
import { useSession } from "@/stores/session";
import { useUI } from "@/stores/ui";

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
  it("does not mount page content or the top bar until the session is ready", () => {
    // Mounting during boot fired every page query without a token (401 burst on reload).
    useSession.setState({ user: null, status: "loading" });
    render(
      <Shell>
        <p>content</p>
      </Shell>,
    );
    expect(screen.queryByText("content")).toBeNull();
    expect(screen.queryByRole("banner")).toBeNull();
    expect(screen.getByLabelText("Loading")).toBeInTheDocument();
  });

  it("has no side rail, only the tab bar and backdrop", () => {
    setup();
    expect(
      screen.queryByRole("navigation", { name: "Main" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Primary" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("backdrop")).toBeInTheDocument();
  });

  it("sets data-transparency when reduce_transparency is on", () => {
    settings.data = { reduce_transparency: true };
    const { container } = setup();
    expect(container.querySelector("[data-density]")).toHaveAttribute(
      "data-transparency",
      "reduced",
    );
    settings.data = undefined;
  });

  it("pads main for the tab bar and safe area", () => {
    setup();
    expect(screen.getByRole("main").className).toContain(
      "env(safe-area-inset-bottom)",
    );
  });

  it("frames main at 2400px centred", () => {
    setup();
    expect(screen.getByRole("main")).toHaveClass(
      "mx-auto",
      "w-full",
      "max-w-[2400px]",
      "px-4",
      "md:px-8",
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

  it("exposes density on the root element", () => {
    useUI.setState({ density: "compact" });
    const { container } = setup();
    expect(container.querySelector("[data-density]")).toHaveAttribute(
      "data-density",
      "compact",
    );
    useUI.setState({ density: "comfortable" });
  });

  it("does not render a floating Help button (help lives in the avatar menu)", () => {
    setup();
    expect(
      screen.queryByRole("button", { name: "Help menu" }),
    ).not.toBeInTheDocument();
  });
});
