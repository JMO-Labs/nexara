/**
 * @file tests/unit/motion/home-motion.test.tsx
 * @brief Home motion pass: entrance stagger, phone accordion, tile link.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { Calendar } from "lucide-react";

let reduced = false;
const animateMock = vi.hoisted(() =>
  vi.fn(() => ({ then: (r: () => void) => r() })),
);
const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/app",
}));
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced, animate: animateMock };
});
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) =>
    sel({ user: { id: "u1", display_name: "Alice" } }),
}));
vi.mock("@/hooks/useHomeChats", () => ({
  useHomeChats: () => ({ data: { items: [] } }),
}));
vi.mock("@/components/home/Greeting", () => ({
  Greeting: () => <h1>hi</h1>,
}));
vi.mock("@/components/home/ScopeBar", () => ({ ScopeBar: () => <div /> }));
vi.mock("@/components/home/PeopleStrip", () => ({
  PeopleStrip: () => <div />,
}));
vi.mock("@/components/home/NeedsChips", () => ({ NeedsChips: () => <div /> }));
vi.mock("@/components/home/tiles/FeedTile", () => ({
  FeedTile: () => <div />,
}));
vi.mock("@/components/home/tiles/ChatsTile", () => ({
  ChatsTile: () => <div />,
}));
vi.mock("@/components/home/tiles/UpNextTile", () => ({
  UpNextTile: () => <div />,
}));
vi.mock("@/components/home/HomeSideColumn", () => ({
  HomeSideColumn: () => <div />,
}));
vi.mock("@/components/home/tiles/OnThisDayTile", () => ({
  OnThisDayTile: () => null,
}));
vi.mock("@/components/home/tiles/PhotosTile", () => ({
  PhotosTile: () => <div />,
}));

async function loadPage() {
  vi.resetModules();
  return (await import("@/app/app/page")).default;
}

function hasOpacityZero(root: HTMLElement) {
  return Array.from(root.querySelectorAll<HTMLElement>("*")).some(
    (el) => el.style.opacity === "0",
  );
}

beforeEach(() => {
  reduced = false;
  animateMock.mockClear();
  push.mockClear();
});

describe("home page entrance", () => {
  it("reduced motion: nothing starts at opacity 0", async () => {
    reduced = true;
    const Page = await loadPage();
    const { container } = render(<Page />);
    expect(hasOpacityZero(container)).toBe(false);
  });

  it("first mount animates sections in; later mounts render at rest", async () => {
    const Page = await loadPage();
    const first = render(<Page />);
    expect(hasOpacityZero(first.container)).toBe(true);
    first.unmount();
    const second = render(<Page />);
    expect(hasOpacityZero(second.container)).toBe(false);
  });
});

describe("HomeTile motion", () => {
  async function tile() {
    const { HomeTile } = await import("@/components/home/HomeTile");
    return (o: boolean) => (
      <HomeTile
        id="next"
        title="Up next"
        icon={Calendar}
        href="/app/events"
        linkLabel="See calendar"
        open={o}
        onToggle={() => {}}
      >
        <p>tile body</p>
      </HomeTile>
    );
  }

  it("phone: opening animates body height; no inline height at rest", async () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as never;
    const mk = await tile();
    const { rerender } = render(mk(false));
    expect(animateMock).not.toHaveBeenCalled();
    rerender(mk(true));
    expect(animateMock).toHaveBeenCalledTimes(1);
    const body = screen.getByText("tile body").parentElement!;
    expect(body.style.height).toBe("");
  });

  it("reduced motion: opening does not animate", async () => {
    reduced = true;
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as never;
    const mk = await tile();
    const { rerender } = render(mk(false));
    rerender(mk(true));
    expect(animateMock).not.toHaveBeenCalled();
  });

  it("plain left click animates then pushes href", async () => {
    const mk = await tile();
    render(mk(false));
    const link = screen.getByRole("link", { name: "See calendar" });
    await act(async () => {
      fireEvent.click(link);
    });
    expect(animateMock).toHaveBeenCalled();
    expect(push).toHaveBeenCalledWith("/app/events");
  });

  it("modifier click is left to the browser", async () => {
    const mk = await tile();
    render(mk(false));
    const notPrevented = fireEvent.click(
      screen.getByRole("link", { name: "See calendar" }),
      { ctrlKey: true },
    );
    expect(notPrevented).toBe(true);
    expect(animateMock).not.toHaveBeenCalled();
  });

  it("reduced motion: click is not intercepted", async () => {
    reduced = true;
    const mk = await tile();
    render(mk(false));
    const notPrevented = fireEvent.click(
      screen.getByRole("link", { name: "See calendar" }),
    );
    expect(notPrevented).toBe(true);
    expect(animateMock).not.toHaveBeenCalled();
  });
});
