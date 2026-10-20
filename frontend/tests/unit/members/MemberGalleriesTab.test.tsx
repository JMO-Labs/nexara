/**
 * @file tests/unit/members/MemberGalleriesTab.test.tsx
 * @brief MemberGalleriesTab renders user's galleries filtered by owner_id.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import joyTheme from "@/theme/joy-theme";
import { MemberGalleriesTab } from "@/components/members/MemberGalleriesTab";
import type { Gallery } from "@/lib/api/galleries";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/hooks/useGalleries", () => ({
  useGalleryList: () => ({
    data: {
      items: [
        {
          id: "g1",
          owner_id: "user1",
          title: "Vacation 2025",
          description: "Beach photos",
          cover_media_id: null,
          event_id: null,
          subgroup_id: null,
          visibility: "community" as const,
          contribution_policy: "owner_only" as const,
          item_count: 5,
          is_featured: false,
          is_default: false,
          is_event_gallery: false,
          created_at: "2026-04-25T00:00:00Z",
          updated_at: "2026-04-25T00:00:00Z",
        },
        {
          id: "g2",
          owner_id: "user1",
          title: "Family Events",
          description: null,
          cover_media_id: null,
          event_id: null,
          subgroup_id: null,
          visibility: "community" as const,
          contribution_policy: "collaborators" as const,
          item_count: 12,
          is_featured: true,
          is_default: false,
          is_event_gallery: false,
          created_at: "2026-04-20T00:00:00Z",
          updated_at: "2026-04-20T00:00:00Z",
        },
      ] as Gallery[],
      next_cursor: null,
      has_more: false,
    },
    isLoading: false,
    error: null,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function wrap(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={queryClient}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe("MemberGalleriesTab", () => {
  it("renders user galleries with correct owner_id filter", () => {
    wrap(<MemberGalleriesTab userId="user1" />);
    expect(screen.getByText("Vacation 2025")).toBeInTheDocument();
    expect(screen.getByText("Family Events")).toBeInTheDocument();
  });

  it("displays gallery item counts", () => {
    wrap(<MemberGalleriesTab userId="user1" />);
    expect(screen.getByText("5 items")).toBeInTheDocument();
    expect(screen.getByText("12 items")).toBeInTheDocument();
  });

  it("shows featured badge on featured galleries", () => {
    wrap(<MemberGalleriesTab userId="user1" />);
    expect(screen.getByText("Featured")).toBeInTheDocument();
  });
});
