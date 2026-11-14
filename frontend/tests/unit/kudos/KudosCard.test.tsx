/**
 * @file tests/unit/kudos/KudosCard.test.tsx
 * @brief KudosCard renders recipient, message, sender in distinct style.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KudosCard } from "@/components/feed/KudosCard";

const recipient = {
  id: "u2",
  username: "ana",
  display_name: "Ana Lima",
  avatar_url: null,
};

describe("KudosCard", () => {
  it("shows bold recipient, message, sender and trophy", () => {
    render(
      <KudosCard
        recipient={recipient}
        message="Great job!"
        authorName="Bob"
        createdAt="2026-01-01T00:00:00Z"
      />,
    );
    expect(screen.getByText("Ana Lima").className).toMatch(/font-bold/);
    expect(screen.getByText("Great job!")).toBeInTheDocument();
    expect(screen.getByText(/Bob/)).toBeInTheDocument();
    expect(screen.getByTestId("kudos-trophy")).toBeInTheDocument();
    expect(screen.getByRole("article").className).toMatch(/purple/);
  });

  it("omits message when absent", () => {
    render(
      <KudosCard
        recipient={recipient}
        message={null}
        createdAt="2026-01-01T00:00:00Z"
      />,
    );
    expect(screen.queryByTestId("kudos-message")).toBeNull();
  });
});
