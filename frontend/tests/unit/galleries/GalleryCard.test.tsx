/**
 * @file tests/unit/galleries/GalleryCard.test.tsx
 * @brief Renders title, item count, fires onSelect.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GalleryCard } from "@/components/galleries/GalleryCard";
import type { Gallery } from "@/lib/api/galleries";

const g: Gallery = {
  id: "g1",
  owner_id: "u1",
  title: "Trip 2026",
  description: null,
  cover_media_id: null,
  event_id: null,
  subgroup_id: null,
  visibility: "community",
  contribution_policy: "owner_only",
  item_count: 7,
  is_featured: true,
  is_default: false,
  is_event_gallery: false,
  created_at: "2026-04-25T00:00:00Z",
  updated_at: "2026-04-25T00:00:00Z",
};

function wrap(ui: React.ReactNode) {
  return render(ui);
}

describe("GalleryCard", () => {
  it("renders title, count, featured chip", () => {
    wrap(<GalleryCard gallery={g} onSelect={() => {}} />);
    expect(screen.getByText("Trip 2026")).toBeInTheDocument();
    expect(screen.getByText(/7 items/)).toBeInTheDocument();
    expect(screen.getByText("Featured")).toBeInTheDocument();
  });
  it("renders owner avatar and name at bottom", () => {
    wrap(<GalleryCard gallery={g} onSelect={() => {}} />);
    // Avatar is rendered (img with alt text or Avatar component)
    const avatar = screen.getByTestId("gallery-card-owner-avatar");
    expect(avatar).toBeInTheDocument();
    // Owner name is visible
    const ownerName = screen.getByText("u1");
    expect(ownerName).toBeInTheDocument();
  });
  it("fires onSelect on click", () => {
    const fn = vi.fn();
    wrap(<GalleryCard gallery={g} onSelect={fn} />);
    fireEvent.click(screen.getByRole("button"));
    expect(fn).toHaveBeenCalledWith("g1");
  });
  it("shows Event gallery badge when event_id is set", () => {
    wrap(
      <GalleryCard gallery={{ ...g, event_id: "e1" }} onSelect={() => {}} />,
    );
    expect(screen.getByText("Event gallery")).toBeInTheDocument();
  });
  it("shows no Event gallery badge when event_id is null", () => {
    wrap(<GalleryCard gallery={g} onSelect={() => {}} />);
    expect(screen.queryByText("Event gallery")).toBeNull();
  });
});
