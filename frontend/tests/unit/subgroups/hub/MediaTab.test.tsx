/**
 * @file tests/unit/subgroups/hub/MediaTab.test.tsx
 * @brief Hub MediaTab: source Segmented drives the query, photos render.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { MediaTab } from "@/components/subgroups/hub/MediaTab";
import type { SubgroupDetail } from "@/lib/api/subgroups";

const q = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/useSubgroupMedia", () => ({
  useSubgroupMedia: (p: unknown) => q(p),
}));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: ({ alt }: { alt?: string }) => <span>{alt}</span>,
}));

const sg = { id: "s1", slug: "fam" } as unknown as SubgroupDetail;

beforeEach(() => {
  q.mockReturnValue({
    data: {
      pages: [
        {
          items: [
            {
              media_id: "m1",
              source_title: "Picnic",
              media: { alt_text: null },
            },
          ],
        },
      ],
    },
    isLoading: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    error: null,
  });
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
});

describe("hub MediaTab", () => {
  it("renders photos and the source radiogroup", () => {
    render(<MediaTab subgroup={sg} />);
    expect(screen.getByText("Picnic")).toBeInTheDocument();
    expect(
      screen.getByRole("radiogroup", { name: "Media source" }),
    ).toBeVisible();
    expect(screen.getByRole("radio", { name: "All" })).toBeChecked();
  });

  it("changing source refetches with that source", async () => {
    render(<MediaTab subgroup={sg} />);
    await userEvent.click(screen.getByRole("radio", { name: "Events" }));
    expect(q).toHaveBeenLastCalledWith({
      slug: "fam",
      source: "event",
      limit: 60,
    });
  });
});
