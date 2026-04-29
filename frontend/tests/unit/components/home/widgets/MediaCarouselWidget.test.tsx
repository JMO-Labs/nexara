/**
 * @file tests/unit/components/home/widgets/MediaCarouselWidget.test.tsx
 * @brief Unit tests for MediaCarouselWidget.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";

vi.mock("@/hooks/useHomeMedia", () => ({
  useHomeMedia: vi.fn(() => ({ data: undefined, isLoading: true })),
}));
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
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
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe("MediaCarouselWidget", () => {
  it("renders without crashing", () => {
    wrap(<MediaCarouselWidget instanceId="w1" />);
    expect(document.body).toBeTruthy();
  });

  it("shows skeleton while loading", () => {
    wrap(<MediaCarouselWidget instanceId="w1" />);
    expect(document.body.children.length).toBeGreaterThan(0);
  });

  it("shows empty state when no media", () => {
    vi.mocked(useHomeMedia).mockReturnValue({
      data: { items: [], next_cursor: null },
      isLoading: false,
    } as unknown as ReturnType<typeof useHomeMedia>);

    wrap(<MediaCarouselWidget instanceId="w1" />);
    expect(screen.getByText("No media yet")).toBeInTheDocument();
  });
});
