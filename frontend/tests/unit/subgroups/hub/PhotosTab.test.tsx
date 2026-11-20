/**
 * @file tests/unit/subgroups/hub/PhotosTab.test.tsx
 * @brief Photos tab: Albums | All photos switch over the two existing views.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PhotosTab } from "@/components/subgroups/hub/PhotosTab";
import type { SubgroupDetail } from "@/lib/api/subgroups";

vi.mock("@/components/subgroups/hub/GalleriesTab", () => ({
  GalleriesTab: () => <div>albums-view</div>,
}));
vi.mock("@/components/subgroups/hub/MediaTab", () => ({
  MediaTab: () => <div>all-photos-view</div>,
}));

const subgroup = { id: "sg1", slug: "hiking" } as SubgroupDetail;

describe("PhotosTab", () => {
  it("shows Albums by default and switches to All photos", () => {
    render(<PhotosTab subgroup={subgroup} />);
    expect(screen.getByText("albums-view")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "All photos" }));
    expect(screen.getByText("all-photos-view")).toBeInTheDocument();
    expect(screen.queryByText("albums-view")).toBeNull();
  });
});
