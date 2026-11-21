/**
 * @file tests/unit/members/MemberProfilePage.test.tsx
 * @brief Member profile: header content, actions, tabs, self and error states.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import MemberProfilePage from "@/app/app/members/[id]/page";
import { useSession } from "@/stores/session";
import type { CurrentUser } from "@/lib/api/users";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "u2" }),
  useRouter: () => ({ push }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/components/members/MemberGalleriesTab", () => ({
  MemberGalleriesTab: () => <div>galleries-tab</div>,
}));
const mutateAsync = vi.fn();
vi.mock("@/hooks/useChat", () => ({
  useCreateDm: () => ({ mutateAsync, isPending: false }),
}));

let profileState: Record<string, unknown> = {};
let connection: unknown = null;
vi.mock("@/hooks/useMembers", () => ({
  useMemberProfile: () => profileState,
  useMemberConnection: () => ({ data: connection }),
}));

const profile = {
  id: "u2",
  username: "tomas",
  display_name: "Tomás Reyes",
  avatar_url: null,
  bio: "Loves chess.",
  title: null,
  pronouns: null,
  location: null,
  website_url: null,
  role: "member",
  created_at: "2026-01-01T00:00:00Z",
  last_seen_at: null,
};

const asUser = (id: string) =>
  useSession.getState().setUser({ id } as unknown as CurrentUser);

describe("MemberProfilePage", () => {
  beforeEach(() => {
    useSession.getState().reset();
    push.mockReset();
    mutateAsync.mockReset();
    profileState = { data: profile, isLoading: false, isError: false };
    connection = {
      user_id: "u2",
      username: "tomas",
      display_name: "Tomás Reyes",
      avatar_url: null,
      online: true,
      last_seen_at: null,
      shared_groups: [
        { id: "g1", name: "Chess Club", accent_color: "#112233" },
      ],
      primary_group_id: "g1",
    };
  });

  it("shows name, @username, bio and shared groups but never the raw id", () => {
    asUser("u1");
    renderWithProviders(<MemberProfilePage />);
    expect(screen.getByText("Tomás Reyes")).toBeInTheDocument();
    expect(screen.getByText(/@tomas/)).toBeInTheDocument();
    expect(screen.getByText("Loves chess.")).toBeInTheDocument();
    expect(screen.getByText("Chess Club")).toBeInTheDocument();
    expect(screen.queryByText(/u2/)).toBeNull();
  });

  it("hero shows joined date and an About card beside the tabs", () => {
    asUser("u1");
    renderWithProviders(<MemberProfilePage />);
    const header = screen.getByRole("region", { name: "Profile" });
    expect(header).toHaveTextContent(/Joined \w+ \d{4}/);
    expect(screen.getByRole("region", { name: "About" })).toBeInTheDocument();
  });

  it("uses the display name as the page h1, not a generic Profile title", () => {
    asUser("u1");
    renderWithProviders(<MemberProfilePage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Tomás Reyes" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { level: 1, name: "Profile" }),
    ).toBeNull();
    expect(
      screen.queryByRole("heading", { level: 2, name: "Tomás Reyes" }),
    ).toBeNull();
  });

  it("back link returns to the Community page", () => {
    asUser("u1");
    renderWithProviders(<MemberProfilePage />);
    expect(screen.getByRole("link", { name: "Community" })).toHaveAttribute(
      "href",
      "/app/community",
    );
  });

  it("opens a DM from the Message button", async () => {
    asUser("u1");
    mutateAsync.mockResolvedValue({ id: "c9" });
    renderWithProviders(<MemberProfilePage />);
    fireEvent.click(screen.getByRole("button", { name: "Message" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/app/chat/c9"));
    expect(mutateAsync).toHaveBeenCalledWith("u2");
  });

  it("offers Nudge and a Block action in the overflow menu", () => {
    asUser("u1");
    renderWithProviders(<MemberProfilePage />);
    expect(screen.getByRole("button", { name: /Nudge/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "More actions" }));
    expect(screen.getByRole("button", { name: /^Block / })).toBeInTheDocument();
  });

  it("hides social actions on your own profile", () => {
    asUser("u2");
    renderWithProviders(<MemberProfilePage />);
    expect(screen.queryByRole("button", { name: "Message" })).toBeNull();
    expect(screen.queryByRole("button", { name: "More actions" })).toBeNull();
  });

  it("switches between Photos and Groups tabs (no Posts tab)", () => {
    asUser("u1");
    renderWithProviders(<MemberProfilePage />);
    expect(screen.getByText("galleries-tab")).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Posts" })).toBeNull();
    fireEvent.click(screen.getByRole("radio", { name: "Groups" }));
    expect(screen.queryByText("galleries-tab")).toBeNull();
    expect(screen.getAllByText("Chess Club").length).toBeGreaterThan(0);
  });

  it("shows empty groups copy when none are shared", () => {
    asUser("u1");
    connection = null;
    renderWithProviders(<MemberProfilePage />);
    fireEvent.click(screen.getByRole("radio", { name: "Groups" }));
    expect(screen.getByText("No shared groups")).toBeInTheDocument();
  });

  it("shows a not-found state when the profile fails to load", () => {
    asUser("u1");
    profileState = { data: undefined, isLoading: false, isError: true };
    renderWithProviders(<MemberProfilePage />);
    expect(screen.getByText("Member not found")).toBeInTheDocument();
  });
});
