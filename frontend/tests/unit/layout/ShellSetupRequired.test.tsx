/**
 * @file tests/unit/layout/Shell.test.tsx
 * @brief Shell redirects to Settings > Security on 2fa_setup_required.
 */
import { describe, it, expect, vi } from "vitest";
import { act, render } from "@testing-library/react";

const nav = vi.hoisted(() => ({
  path: "/app",
  search: "",
  replace: vi.fn(),
}));
const gate = vi.hoisted(() => ({ pending: false }));
vi.mock("@/components/onboarding/OnboardingGate", () => ({
  useOnboardingGate: () => ({ pending: gate.pending, loaded: true }),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => nav.path,
  useSearchParams: () => new URLSearchParams(nav.search),
  useRouter: () => ({ replace: nav.replace }),
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

function fire(path: string, search: string) {
  nav.path = path;
  nav.search = search;
  window.history.replaceState(null, "", search ? `${path}?${search}` : path);
  nav.replace.mockClear();
  useSession.setState({
    user: { is_admin: false, role: "member" } as never,
    status: "authenticated",
  });
  render(
    <Shell>
      <p>content</p>
    </Shell>,
  );
  act(() => {
    window.dispatchEvent(new CustomEvent("nx:2fa-setup-required"));
  });
}

describe("Shell 2fa_setup_required", () => {
  it("redirects from another settings tab", () => {
    fire("/app/settings", "tab=profile");
    expect(nav.replace).toHaveBeenCalledWith("/app/settings?tab=security");
  });
  it("redirects from other pages", () => {
    fire("/app", "");
    expect(nav.replace).toHaveBeenCalledWith("/app/settings?tab=security");
  });
  it("routes to the wizard's security step while onboarding is pending", () => {
    gate.pending = true;
    fire("/app", "");
    gate.pending = false;
    expect(nav.replace).toHaveBeenCalledWith("/app/welcome");
  });
  it("stays on Settings > Security", () => {
    fire("/app/settings", "tab=security");
    expect(nav.replace).not.toHaveBeenCalled();
  });
});
