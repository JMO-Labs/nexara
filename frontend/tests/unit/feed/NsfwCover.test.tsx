/**
 * @file tests/unit/feed/NsfwCover.test.tsx
 * @brief NSFW cover reveal, always-show bypass and toggle gating.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NsfwCover, resetRevealed } from "@/components/feed/NsfwCover";
import { NsfwToggle } from "@/components/compose/NsfwToggle";
import { useSession } from "@/stores/session";

let always = false;
let feature = true;
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: { always_show_nsfw: always } }),
}));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => feature }));

const wrap = (ui: React.ReactNode) => (
  <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
);

beforeEach(() => {
  always = false;
  feature = true;
  resetRevealed();
});

describe("NsfwCover", () => {
  it("hides content until the cover button is clicked", async () => {
    render(
      wrap(
        <NsfwCover nsfw itemId="a">
          <p>secret</p>
        </NsfwCover>,
      ),
    );
    const btn = screen.getByRole("button", { name: "Show NSFW content" });
    expect(btn).toHaveTextContent("NSFW — tap to view");
    await userEvent.click(btn);
    expect(
      screen.queryByRole("button", { name: "Show NSFW content" }),
    ).toBeNull();
    expect(screen.getByText("secret")).toBeInTheDocument();
  });

  it("renders plainly when not NSFW or always_show_nsfw", () => {
    always = true;
    render(
      wrap(
        <NsfwCover nsfw itemId="b">
          <p>x</p>
        </NsfwCover>,
      ),
    );
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("stays revealed for the item", async () => {
    const ui = (
      <NsfwCover nsfw itemId="c">
        <p>x</p>
      </NsfwCover>
    );
    const { unmount } = render(wrap(ui));
    await userEvent.click(screen.getByRole("button"));
    unmount();
    render(wrap(ui));
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("NsfwToggle", () => {
  const setAge = (age_group: string) =>
    useSession.setState({ user: { id: "u", age_group } as never });

  it("shows for adults with the feature on", () => {
    setAge("adult");
    render(wrap(<NsfwToggle checked={false} onChange={() => {}} />));
    expect(screen.getByRole("switch", { name: "NSFW" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Hidden from children and teens. Adults see it blurred until they tap.",
      ),
    ).toBeInTheDocument();
  });

  it("is hidden for teens", () => {
    setAge("teen");
    render(wrap(<NsfwToggle checked={false} onChange={() => {}} />));
    expect(screen.queryByRole("switch")).toBeNull();
  });

  it("is hidden when the feature is off", () => {
    setAge("adult");
    feature = false;
    render(wrap(<NsfwToggle checked={false} onChange={() => {}} />));
    expect(screen.queryByRole("switch")).toBeNull();
  });
});
