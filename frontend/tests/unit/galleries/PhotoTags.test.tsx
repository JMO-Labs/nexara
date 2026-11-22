/**
 * @file tests/unit/galleries/PhotoTags.test.tsx
 * @brief PhotoTags: lists tags, tags someone via the picker, remove rights.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

const api = {
  listTags: vi.fn(),
  tagPhoto: vi.fn(),
  removeTag: vi.fn(),
};
vi.mock("@/lib/api/tags", () => ({
  listTags: (...a: unknown[]) => api.listTags(...a),
  tagPhoto: (...a: unknown[]) => api.tagPhoto(...a),
  removeTag: (...a: unknown[]) => api.removeTag(...a),
}));
vi.mock("@/hooks/useMembersList", async (orig) => ({
  ...(await orig<typeof import("@/hooks/useMembersList")>()),
  useMembersList: () => ({
    data: [
      {
        id: "u2",
        username: "ruth",
        display_name: "Ruth Alvarez",
        avatar_url: null,
      },
      { id: "u3", username: "leo", display_name: "Leo Soto", avatar_url: null },
    ],
  }),
}));
vi.mock("@/hooks/useHousehold", () => ({
  useVisibleHousehold: () => ({
    data: [
      {
        id: "p1",
        kind: "pet",
        name: "Biscuit",
        species: "Dog",
        relation: null,
        can_edit: true,
      },
    ],
  }),
}));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: unknown) => unknown) => sel({ user: { id: "me" } }),
}));

import { PhotoTags } from "@/components/galleries/PhotoTags";

const tag = (id: string, user: string, name: string, by = "x") => ({
  id,
  tagged_by: by,
  user: {
    id: user,
    username: name.toLowerCase(),
    display_name: name,
    avatar_url: null,
  },
});

describe("PhotoTags", () => {
  beforeEach(() => Object.values(api).forEach((f) => f.mockReset()));

  it("shows tags; remove only on my tags or ones I added", async () => {
    api.listTags.mockResolvedValue([
      tag("t1", "u2", "Ruth", "me"),
      tag("t2", "u3", "Leo"),
    ]);
    renderWithProviders(<PhotoTags mediaId="m1" />);
    expect(
      await screen.findByRole("link", { name: "Ruth" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Remove tag Ruth")).toBeInTheDocument();
    expect(screen.queryByLabelText("Remove tag Leo")).toBeNull();
  });

  it("tags someone from the picker, skipping people already tagged", async () => {
    api.listTags.mockResolvedValue([tag("t1", "u2", "Ruth")]);
    api.tagPhoto.mockResolvedValue([
      tag("t1", "u2", "Ruth"),
      tag("t3", "u3", "Leo"),
    ]);
    renderWithProviders(<PhotoTags mediaId="m1" />);
    await screen.findByRole("link", { name: "Ruth" });
    fireEvent.click(screen.getByRole("button", { name: /Tag someone/ }));
    fireEvent.change(screen.getByLabelText("Tag someone"), {
      target: { value: "" },
    });
    expect(screen.queryByRole("option", { name: /Ruth/ })).toBeNull();
    fireEvent.mouseDown(screen.getByRole("option", { name: /Leo/ }));
    await waitFor(() =>
      expect(api.tagPhoto).toHaveBeenCalledWith("m1", { user_id: "u3" }),
    );
    expect(
      await screen.findByRole("link", { name: "Leo" }),
    ).toBeInTheDocument();
  });

  it("tags a pet by household id; owner may remove the pet tag", async () => {
    api.listTags.mockResolvedValue([]);
    api.tagPhoto.mockResolvedValue([
      {
        id: "t9",
        tagged_by: "x",
        user: null,
        household: {
          id: "p1",
          name: "Biscuit",
          kind: "pet",
          photo_media_id: null,
        },
      },
    ]);
    renderWithProviders(<PhotoTags mediaId="m1" />);
    fireEvent.click(await screen.findByRole("button", { name: /Tag someone/ }));
    fireEvent.change(screen.getByLabelText("Tag someone"), {
      target: { value: "bis" },
    });
    expect(screen.getByRole("option", { name: /Biscuit/ })).toHaveTextContent(
      "Dog",
    );
    fireEvent.mouseDown(screen.getByRole("option", { name: /Biscuit/ }));
    await waitFor(() =>
      expect(api.tagPhoto).toHaveBeenCalledWith("m1", { household_id: "p1" }),
    );
    expect(
      await screen.findByRole("link", { name: "Biscuit" }),
    ).toHaveAttribute("href", "/app/household/p1");
    expect(screen.getByLabelText("Remove tag Biscuit")).toBeInTheDocument();
  });

  it("renders nothing when the photo isn't visible", async () => {
    api.listTags.mockRejectedValue(new Error("Not found"));
    renderWithProviders(<PhotoTags mediaId="m1" />);
    await waitFor(() => expect(api.listTags).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /Tag someone/ })).toBeNull(),
    );
  });
});
