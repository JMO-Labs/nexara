/**
 * @file tests/unit/subgroups/accent-color.test.tsx
 * @brief Subgroup accent color: header usage, fallback, editor AA warning.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { CoverBand } from "@/components/subgroups/hub/CoverBand";
import { SettingsTab } from "@/components/subgroups/hub/SettingsTab";
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

function wrap(ui: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={{}}>
      <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

describe("subgroup accent color", () => {
  it("CoverBand uses subgroup accent when set", () => {
    const { container } = wrap(
      <CoverBand subgroup={{ ...base, accent_color: "#C6B4F5" }} />,
    );
    expect(container.querySelector("[data-accent-bar]")).toHaveStyle({
      backgroundColor: "#C6B4F5",
    });
  });

  it("CoverBand falls back to community accent var when null", () => {
    const { container } = wrap(<CoverBand subgroup={base} />);
    const bar = container.querySelector("[data-accent-bar]") as HTMLElement;
    expect(bar.getAttribute("style")).toContain("var(--nx-accent");
  });

  it("editor warns when accent fails AA", () => {
    wrap(<SettingsTab subgroup={base} />);
    fireEvent.change(screen.getByLabelText("Accent color"), {
      target: { value: "#1B3524" },
    });
    expect(screen.getByText(/4\.5:1 contrast/)).toBeInTheDocument();
  });
});
