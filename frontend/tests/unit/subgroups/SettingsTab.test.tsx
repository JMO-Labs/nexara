/**
 * @file tests/unit/subgroups/SettingsTab.test.tsx
 * @brief Settings tab: owner-only fields visible; cover upload button present.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { SettingsTab } from "@/components/subgroups/hub/SettingsTab";
import * as mediaApi from "@/lib/api/media";
import * as subgroupApi from "@/lib/api/subgroups";
import type { SubgroupDetail } from "@/lib/api/subgroups";

vi.mock("@/lib/api/media");
vi.mock("@/lib/api/subgroups");

const mockSubgroup: SubgroupDetail = {
  id: "sg1",
  name: "Hiking Club",
  slug: "hiking",
  description: "Outdoor enthusiasts",
  avatar_url: null,
  cover_media_id: null,
  is_private: false,
  join_policy: "open",
  created_by: null,
  parent_id: null,
  archived_at: null,
  created_at: "2026-04-25T00:00:00Z",
  updated_at: "2026-04-25T00:00:00Z",
  member_count: 12,
  my_role: "owner",
  chat_channel_id: null,
  pinned_post_id: null,
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return render(
    <NextIntlClientProvider locale="en" messages={{}}>
      <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

describe("SettingsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders owner-only fields when user is owner", () => {
    wrap(<SettingsTab subgroup={mockSubgroup} />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  it("displays cover upload button for owner", () => {
    wrap(<SettingsTab subgroup={mockSubgroup} />);
    expect(
      screen.getByRole("button", { name: /upload cover/i }),
    ).toBeInTheDocument();
  });

  it("hides settings form when user is not owner/moderator", () => {
    const memberSubgroup = { ...mockSubgroup, my_role: "member" as const };
    wrap(<SettingsTab subgroup={memberSubgroup} />);
    expect(screen.getByText(/permission/i)).toBeInTheDocument();
  });

  it("uploads cover and calls updateSubgroup with cover_media_id", async () => {
    const mockMedia = {
      id: "media-new-cover",
      filename: "cover.jpg",
      content_type: "image/jpeg",
      storage_key: "key",
      thumbnail_key: null,
      size_bytes: 100,
      width: 800,
      height: 600,
      duration_secs: null,
      alt_text: null,
      status: "ready" as const,
      created_at: "2026-04-28T00:00:00Z",
    };

    vi.mocked(mediaApi.uploadFile).mockResolvedValue(mockMedia);
    vi.mocked(subgroupApi.updateSubgroup).mockResolvedValue({
      ...mockSubgroup,
      cover_media_id: "media-new-cover",
    });

    wrap(<SettingsTab subgroup={mockSubgroup} />);

    const uploadBtn = screen.getByRole("button", { name: /upload cover/i });
    expect(uploadBtn).toBeInTheDocument();
    const fileInput = screen.getByLabelText(
      /cover image file/i,
    ) as HTMLInputElement;

    const file = new File(["test"], "cover.jpg", { type: "image/jpeg" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(mediaApi.uploadFile).toHaveBeenCalledWith(
        file,
        expect.any(Function),
      );
    });

    await waitFor(() => {
      expect(subgroupApi.updateSubgroup).toHaveBeenCalledWith(
        "hiking",
        expect.objectContaining({
          cover_media_id: "media-new-cover",
        }),
      );
    });
  });
});
