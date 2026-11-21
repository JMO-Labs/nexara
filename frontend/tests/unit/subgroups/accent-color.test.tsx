/**
 * @file tests/unit/subgroups/accent-color.test.tsx
 * @brief Subgroup accent color: header usage, fallback, editor validation.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { CoverBand } from "@/components/subgroups/hub/CoverBand";
import { SettingsTab } from "@/components/subgroups/hub/SettingsTab";
import { GROUP_PALETTE } from "@/lib/groupColor";
import type { SubgroupDetail } from "@/lib/api/subgroups";

vi.mock("@/lib/api/media");
vi.mock("@/lib/api/subgroups");

const base: SubgroupDetail = {
  id: "sg1",
  name: "Hiking Club",
  slug: "hiking",
  description: null,
  avatar_url: null,
  cover_media_id: null,
  accent_color: null,
  is_private: false,
  join_policy: "open",
  created_by: null,
  parent_id: null,
  archived_at: null,
  created_at: "2026-04-25T00:00:00Z",
  updated_at: "2026-04-25T00:00:00Z",
  member_count: 3,
  my_role: "owner",
  is_member: true,
  chat_channel_id: null,
  pinned_post_id: null,
};

function rgbToHex(rgb: string): string {
  const m = rgb.match(/\d+/g);
  if (!m) return rgb.toLowerCase();
  return `#${m
    .slice(0, 3)
    .map((n) => Number(n).toString(16).padStart(2, "0"))
    .join("")}`;
}

function wrap(ui: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={{}}>
      <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

describe("subgroup accent color", () => {
  it("CoverBand tints its background with the subgroup accent when set", () => {
    const { container } = wrap(
      <CoverBand subgroup={{ ...base, accent_color: "#C6B4F5" }} />,
    );
    const band = container.firstElementChild as HTMLElement;
    expect(band.style.background).toContain("rgb(198, 180, 245)");
    expect(band.style.background).toContain("25%");
  });

  it("CoverBand falls back to groupColor palette when null", () => {
    const { container } = wrap(<CoverBand subgroup={base} />);
    const band = container.firstElementChild as HTMLElement;
    const palette = GROUP_PALETTE.map((c) => c.toLowerCase());
    const rgb = band.style.background.match(/rgb\([^)]*\)/)?.[0] ?? "";
    expect(palette).toContain(rgbToHex(rgb).toLowerCase());
  });

  it("accepts any hex (decorative only) and flags malformed input", () => {
    wrap(<SettingsTab subgroup={base} />);
    const field = screen.getByLabelText("Accent color");
    fireEvent.change(field, { target: { value: "#1B3524" } });
    expect(screen.queryByText(/hex color like/)).toBeNull();
    fireEvent.change(field, { target: { value: "#12" } });
    expect(screen.getByText(/hex color like/)).toBeInTheDocument();
  });
});
