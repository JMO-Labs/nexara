/**
 * @file tests/unit/moderation/ModerationQueueStates.test.tsx
 * @brief Empty, error and loading states for the moderation queue.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import * as moderation from "@/hooks/useModeration";
import { ModerationQueue } from "@/components/moderation/ModerationQueue";

vi.mock("@/hooks/useModeration");

beforeEach(() => {
  vi.mocked(moderation.useReportAction).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
});

describe("ModerationQueue states", () => {
  it("shows an all-clear empty state", () => {
    vi.mocked(moderation.useReports).mockReturnValue({
      isLoading: false,
      isError: false,
      data: { items: [] },
    } as never);
    render(<ModerationQueue />);
    expect(screen.getByRole("heading", { name: "All clear" })).toBeVisible();
    expect(
      screen.getByText("No reports are waiting for review."),
    ).toBeInTheDocument();
  });

  it("shows the error as an alert notice", () => {
    vi.mocked(moderation.useReports).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    } as never);
    render(<ModerationQueue />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Couldn't load reports.",
    );
  });

  it("shows glass skeleton rows while loading", () => {
    vi.mocked(moderation.useReports).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as never);
    render(<ModerationQueue />);
    expect(
      screen.getByRole("status", { name: "Loading reports" }),
    ).toBeVisible();
  });
});
