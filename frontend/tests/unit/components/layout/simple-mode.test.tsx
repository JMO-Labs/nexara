/**
 * @file tests/unit/components/layout/simple-mode.test.tsx
 * @brief Simple mode: data-simple sync, 4-item nav, More sheet, hover-only CSS.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const mocks = vi.hoisted(() => ({
  feature: true,
  settings: { simple_mode: true } as { simple_mode?: boolean } | undefined,
  update: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/app",
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => mocks.feature }));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: mocks.settings }),
  useUpdateSettings: () => ({ mutate: mocks.update }),
}));
vi.mock("@/hooks/useChat", () => ({ useChatRealtime: () => ({ unread: {} }) }));
vi.mock("@/hooks/useSignOut", () => ({ useSignOut: () => vi.fn() }));
vi.mock("@/components/layout/CreateMenu", () => ({ CreateMenu: () => null }));

import { SimpleModeSync } from "@/components/layout/SimpleModeSync";
import { TopNav } from "@/components/layout/TopNav";
import { BottomTabBar } from "@/components/layout/BottomTabBar";
import { MoreSheet } from "@/components/layout/MoreSheet";
import { useSimpleMode } from "@/stores/simpleMode";
import { useSession } from "@/stores/session";

const ROOT = join(__dirname, "../../../..");
const PRIMARY = ["Home", "Photos", "Family", "Calendar"];

beforeEach(() => {
  mocks.feature = true;
  mocks.settings = { simple_mode: true };
  mocks.update.mockReset();
  useSimpleMode.setState({ on: false });
  useSession.setState({
    user: { role: "member" } as never,
    status: "authenticated",
  });
});

describe("SimpleModeSync", () => {
  it("sets data-simple when the setting is on", () => {
    render(<SimpleModeSync />);
    expect(document.documentElement.dataset.simple).toBe("1");
    expect(useSimpleMode.getState().on).toBe(true);
  });

  it("does nothing when the setting is off", () => {
    mocks.settings = { simple_mode: false };
    render(<SimpleModeSync />);
    expect(document.documentElement.dataset.simple).toBeUndefined();
  });

  it("does nothing when the community feature is off", () => {
    mocks.feature = false;
    render(<SimpleModeSync />);
    expect(document.documentElement.dataset.simple).toBeUndefined();
  });
});

describe("simple nav", () => {
  beforeEach(() => useSimpleMode.setState({ on: true }));

  it("top nav shows exactly Home, Photos, Family, Calendar", () => {
    render(<TopNav />);
    const names = screen.getAllByRole("link").map((l) => l.textContent);
    expect(names).toEqual(PRIMARY);
  });

  it("tab bar shows the same four", () => {
    render(<BottomTabBar />);
    const names = screen.getAllByRole("link").map((l) => l.textContent);
    expect(names).toEqual(PRIMARY);
  });

  it("More keeps Settings and offers turning simple mode off", () => {
    render(<MoreSheet open onClose={vi.fn()} />);
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Community" })).toBeNull();
    screen.getByRole("button", { name: "Turn off simple mode" }).click();
    expect(mocks.update).toHaveBeenCalledWith({ simple_mode: false });
  });
});

describe("hover-only controls", () => {
  it("globals.css reveals .hover-only in simple mode", () => {
    const css = readFileSync(join(ROOT, "app/globals.css"), "utf8");
    expect(css).toMatch(/\[data-simple\] \.hover-only\s*\{\s*opacity: 1;/);
  });

  it.each([
    "components/chat/MessageItem.tsx",
    "components/chat/ThreadRow.tsx",
    "components/feed/PostMedia.tsx",
    "components/galleries/galleries-page/GalleryDrawer.tsx",
  ])("%s marks its hover-reveal control", (f) => {
    expect(readFileSync(join(ROOT, f), "utf8")).toContain("hover-only");
  });
});
