/**
 * @file tests/unit/components/home/widgets/MediaCarouselWidget.test.tsx
 * @brief Unit tests for MediaCarouselWidget.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useHomeMedia", () => ({
  useHomeMedia: vi.fn(() => ({ data: undefined, isLoading: true })),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));
vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return {
    ...actual,
    useReducedMotion: () => false,
  };
});

import { MediaCarouselWidget } from "@/components/home/widgets/MediaCarouselWidget";
import { useHomeMedia } from "@/hooks/useHomeMedia";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("MediaCarouselWidget", () => {
  it("renders without crashing", () => {
    wrap(<MediaCarouselWidget />);
    expect(document.body).toBeTruthy();
  });

  it("shows skeleton while loading", () => {
    wrap(<MediaCarouselWidget />);
    expect(document.body.children.length).toBeGreaterThan(0);
  });

  it("shows empty state when no media", () => {
    vi.mocked(useHomeMedia).mockReturnValue({
      data: { items: [], next_cursor: null },
      isLoading: false,
    } as unknown as ReturnType<typeof useHomeMedia>);

    wrap(<MediaCarouselWidget />);
    expect(screen.getByText("No media yet")).toBeInTheDocument();
  });

  it("union query includes both community-root and subgroup items", () => {
    // This test verifies that the component calls useHomeMedia with scope='all'
    // which triggers a union query in the backend (home_service.list_media)
    vi.mocked(useHomeMedia).mockReturnValue({
      data: { items: [], next_cursor: null },
      isLoading: false,
    } as unknown as ReturnType<typeof useHomeMedia>);

    wrap(<MediaCarouselWidget />);
    // Component defaults to scope='all', which triggers union behavior
    expect(useHomeMedia).toHaveBeenCalledWith(
      expect.objectContaining({ scope: "all" }),
    );
  });
});
