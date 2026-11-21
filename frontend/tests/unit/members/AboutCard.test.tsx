/**
 * @file tests/unit/members/AboutCard.test.tsx
 * @brief AboutCard renders only fields the API sent, with useful links.
 */
import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { AboutCard } from "@/components/members/AboutCard";
import type { UserProfile } from "@/lib/api/users";

const base = {
  id: "u1",
  username: "ruth",
  display_name: "Ruth Alvarez",
  avatar_url: null,
  bio: null,
  title: null,
  pronouns: null,
  location: null,
  website_url: null,
  role: "member",
  created_at: "2026-01-01T00:00:00Z",
  last_seen_at: null,
} as UserProfile;

describe("AboutCard", () => {
  it("shows shared fields with tel/maps/social links and vCard", () => {
    renderWithProviders(
      <AboutCard
        isSelf={false}
        profile={{
          ...base,
          phone: "(555) 010-0",
          address: "1 Main St",
          links: [{ label: "", url: "https://instagram.com/ruth" }],
          skills: ["quilting"],
        }}
      />,
    );
    expect(screen.getByRole("link", { name: "(555) 010-0" })).toHaveAttribute(
      "href",
      "tel:5550100",
    );
    expect(
      screen.getByRole("link", { name: "Open in Maps" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Instagram" })).toHaveAttribute(
      "rel",
      expect.stringContaining("noopener"),
    );
    expect(screen.getByText("quilting")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Add to contacts/ }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Emergency contact")).toBeNull();
  });

  it("empty states differ for self and others", () => {
    const { unmount } = renderWithProviders(
      <AboutCard isSelf={false} profile={base} />,
    );
    expect(screen.getByText(/hasn't shared any details/)).toBeInTheDocument();
    unmount();
    renderWithProviders(<AboutCard isSelf profile={base} />);
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute(
      "href",
      "/app/settings?tab=profile",
    );
  });
});
