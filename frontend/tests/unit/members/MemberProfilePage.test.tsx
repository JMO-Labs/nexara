/**
 * @file tests/unit/members/MemberProfilePage.test.tsx
 * @brief Member profile shows Block for other users, hides it for self.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import MemberProfilePage from "@/app/app/members/[id]/page";
import { useSession } from "@/stores/session";
import type { CurrentUser } from "@/lib/api/users";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "u2" }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/components/members/MemberGalleriesTab", () => ({
  MemberGalleriesTab: () => null,
}));

const asUser = (id: string) =>
  useSession.getState().setUser({ id } as unknown as CurrentUser);

describe("MemberProfilePage", () => {
  beforeEach(() => useSession.getState().reset());

  it("shows Block for another member", () => {
    asUser("u1");
    render(<MemberProfilePage />);
    expect(screen.getByRole("button", { name: /^Block / })).toBeInTheDocument();
  });

  it("hides Block on your own profile", () => {
    asUser("u2");
    render(<MemberProfilePage />);
    expect(screen.queryByRole("button", { name: /^Block / })).toBeNull();
  });
});
