/**
 * @file tests/unit/subgroups/hub/CoverBand.test.tsx
 * @brief Cover band: no accent rail, compact height without cover, medium title.
 */
import * as React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CoverBand } from "@/components/subgroups/hub/CoverBand";
import type { SubgroupDetail } from "@/lib/api/subgroups";

const sg = {
  id: "sg1",
  name: "Hiking Club",
  slug: "hiking",
  accent_color: "#83A2DB",
  cover_media_id: null,
  member_count: 12,
  is_private: false,
} as unknown as SubgroupDetail;

describe("CoverBand", () => {
  it("has no solid accent bar rail", () => {
    const { container } = render(<CoverBand subgroup={sg} />);
    expect(container.querySelector("[data-accent-bar]")).toBeNull();
  });

  it("uses a compact band height when there is no cover image", () => {
    const { container } = render(<CoverBand subgroup={sg} />);
    const band = container.firstElementChild as HTMLElement;
    expect(band.className).toContain("h-[140px]");
    expect(band.className).toContain("md:h-[160px]");
  });

  it("renders the title at medium weight", () => {
    render(<CoverBand subgroup={sg} />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Hiking Club" }),
    ).toHaveClass("font-medium");
  });
});
