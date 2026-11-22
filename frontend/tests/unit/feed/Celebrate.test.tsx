/**
 * @file tests/unit/feed/Celebrate.test.tsx
 * @brief Celebrate posts: hero banner and the composer payload.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CelebrateHero } from "@/components/feed/CelebrateHero";
import type { Celebration } from "@/lib/api/posts";

const mutate = vi.fn();
vi.mock("@/hooks/usePosts", () => ({
  useCreatePost: () => ({ mutate, isPending: false }),
}));
vi.mock("@/hooks/useMembersList", () => ({
  useMembersList: () => ({ data: [{ id: "u1", display_name: "Ruth" }] }),
}));
vi.mock("@/hooks/useHousehold", () => ({
  useVisibleHousehold: () => ({
    data: [{ id: "h1", kind: "pet", name: "Biscuit" }],
  }),
}));

import { CelebrateComposer } from "@/components/feed/CelebrateComposer";

const c: Celebration = {
  subject_type: "household",
  subject_id: "h1",
  occasion: "gotcha_day",
  name: "Biscuit",
  is_pet: true,
  avatar_url: null,
  photo_media_id: null,
  link: "/app/household/h1",
};

describe("CelebrateHero", () => {
  it("names the occasion and links the pet", () => {
    render(<CelebrateHero c={c} />);
    expect(
      screen.getByRole("link", { name: "Happy gotcha day, Biscuit" }),
    ).toHaveAttribute("href", "/app/household/h1");
  });

  it("stays generic when the viewer can't see the pet", () => {
    render(<CelebrateHero c={{ ...c, name: null, link: null }} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText(/someone special/)).toBeInTheDocument();
  });
});

describe("CelebrateComposer", () => {
  it("offers gotcha day only for pets and posts the celebration", () => {
    render(<CelebrateComposer open onClose={() => {}} />);
    const who = screen.getByRole("combobox");
    fireEvent.change(who, { target: { value: "user:u1" } });
    expect(screen.queryByRole("radio", { name: "Gotcha day" })).toBeNull();
    fireEvent.change(who, { target: { value: "household:h1" } });
    fireEvent.click(screen.getByRole("radio", { name: "Gotcha day" }));
    fireEvent.click(screen.getByRole("button", { name: "Post celebration" }));
    expect(mutate.mock.calls[0][0].celebrate).toEqual({
      subject_type: "household",
      subject_id: "h1",
      occasion: "gotcha_day",
    });
  });
});
