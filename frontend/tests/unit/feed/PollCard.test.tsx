/**
 * @file tests/unit/feed/PollCard.test.tsx
 * @brief PollCard voting/results and composer poll payload validation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { PollCard } from "@/components/feed/PollCard";
import { pollPayload } from "@/components/feed/ComposerAttachments";
import type { Poll } from "@/lib/api/posts";
import { renderWithProviders } from "../../utils/renderWithProviders";

const votePoll = vi.fn();
vi.mock("@/lib/api/polls", () => ({
  votePoll: (...a: unknown[]) => votePoll(...a),
}));

const poll = (p: Partial<Poll> = {}): Poll => ({
  id: "p1",
  post_id: "x",
  poll_type: "single",
  question: "Pizza or tacos?",
  options: [
    {
      id: "a",
      label: "Pizza",
      image_media_id: null,
      position: 0,
      vote_count: 3,
      voters: [],
    },
    {
      id: "b",
      label: "Tacos",
      image_media_id: null,
      position: 1,
      vote_count: 1,
      voters: [],
    },
  ],
  is_anonymous: false,
  result_visibility: "after_vote",
  expires_at: null,
  closed: false,
  total_votes: 4,
  user_vote: null,
  created_at: "2026-11-21T00:00:00Z",
  ...p,
});

describe("PollCard", () => {
  beforeEach(() => {
    votePoll.mockReset().mockResolvedValue({ total_votes: 5 });
  });

  it("hides results before voting and votes on tap", async () => {
    renderWithProviders(<PollCard poll={poll()} />);
    expect(screen.queryByText("75%")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Tacos/ }));
    await waitFor(() => expect(votePoll).toHaveBeenCalledWith("p1", ["b"]));
  });

  it("shows results and my vote after voting", () => {
    renderWithProviders(<PollCard poll={poll({ user_vote: ["a"] })} />);
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByLabelText("Your vote")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Change vote" }),
    ).toBeInTheDocument();
  });

  it("multiple choice needs Vote after ticking", async () => {
    renderWithProviders(<PollCard poll={poll({ poll_type: "multiple" })} />);
    fireEvent.click(screen.getByRole("button", { name: /Pizza/ }));
    fireEvent.click(screen.getByRole("button", { name: /Tacos/ }));
    expect(votePoll).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Vote" }));
    await waitFor(() =>
      expect(votePoll).toHaveBeenCalledWith("p1", ["a", "b"]),
    );
  });

  it("shows lettered options and an animated bar per option", async () => {
    renderWithProviders(<PollCard poll={poll({ user_vote: ["a"] })} />);
    expect(screen.getByRole("group", { name: /Poll: Pizza/ })).toBeTruthy();
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    const bars = screen.getAllByTestId("poll-bar");
    expect(bars[0].className).toMatch(/motion-reduce:transition-none/);
    await waitFor(() => expect(bars[0]).toHaveStyle({ width: "75%" }));
  });

  it("closed poll shows final results and disables options", () => {
    renderWithProviders(<PollCard poll={poll({ closed: true })} />);
    expect(screen.getByText(/Final results/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Pizza/ })).toBeDisabled();
  });
});

describe("pollPayload", () => {
  it("validates and trims", () => {
    expect(
      pollPayload({ question: " ", options: ["a", "b"], multiple: false }),
    ).toMatch(/question/);
    expect(
      pollPayload({ question: "Q", options: ["a", " "], multiple: false }),
    ).toMatch(/two options/);
    expect(
      pollPayload({ question: " Q ", options: ["a", "b", ""], multiple: true }),
    ).toEqual({
      question: "Q",
      poll_type: "multiple",
      options: [{ label: "a" }, { label: "b" }],
    });
  });
});
