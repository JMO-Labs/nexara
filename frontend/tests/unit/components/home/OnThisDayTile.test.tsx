/**
 * @file tests/unit/components/home/OnThisDayTile.test.tsx
 * @brief OnThisDayTile: hidden when empty; groups items by years ago.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/app",
}));
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../../utils/renderWithProviders";
import { OnThisDayTile } from "@/components/home/tiles/OnThisDayTile";

const mocks = vi.hoisted(() => ({ get: vi.fn(), on: true }));
vi.mock("@/lib/api/memories", () => ({ getOnThisDay: mocks.get }));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => mocks.on }));

const post = (id: string, content: string, photo = false) => ({
  id,
  content,
  author: { id: "u", username: "ruth", display_name: "Ruth" },
  media: photo
    ? [{ id: "m", url: "/f", thumbnail_url: "/t", mime_type: "image/jpeg" }]
    : [],
});

describe("OnThisDayTile", () => {
  beforeEach(() => {
    mocks.get.mockReset();
    mocks.on = true;
  });

  it("renders nothing when empty", async () => {
    mocks.get.mockResolvedValue({ items: [], years_ago: [] });
    const { container } = renderWithProviders(
      <OnThisDayTile open={false} onToggle={vi.fn()} />,
    );
    await waitFor(() => expect(mocks.get).toHaveBeenCalled());
    expect(container.querySelector("[data-tile]")).toBeNull();
  });

  it("renders nothing when the feature is off", () => {
    mocks.on = false;
    const { container } = renderWithProviders(
      <OnThisDayTile open={false} onToggle={vi.fn()} />,
    );
    expect(container.querySelector("[data-tile]")).toBeNull();
    expect(mocks.get).not.toHaveBeenCalled();
  });

  it("groups two years into two groups with post links", async () => {
    mocks.get.mockResolvedValue({
      items: [post("p1", "hello"), post("p2", "", true)],
      years_ago: [1, 3],
    });
    renderWithProviders(<OnThisDayTile open onToggle={vi.fn()} />);
    expect(
      await screen.findByRole("heading", { name: "1 year ago", level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "3 years ago", level: 3 }),
    ).toBeInTheDocument();
    const links = screen
      .getAllByRole("link")
      .map((a) => a.getAttribute("href"));
    expect(links).toContain("/app/post/p1");
    expect(links).toContain("/app/post/p2");
    expect(screen.getByText("Shared a photo")).toBeInTheDocument();
  });
});
