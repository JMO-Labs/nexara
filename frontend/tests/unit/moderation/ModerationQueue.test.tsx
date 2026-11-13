/**
 * @file tests/unit/moderation/ModerationQueue.test.tsx
 * @brief Admin moderation queue table, expand and batch actions.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModerationQueue } from "@/components/moderation/ModerationQueue";

const act = vi.fn().mockResolvedValue({});
vi.mock("@/hooks/useModeration", () => ({
  useReports: () => ({
    isLoading: false,
    isError: false,
    data: {
      items: [
        {
          id: "r1",
          reporter_id: "u1",
          target_type: "post",
          target_id: "p1",
          reason: "spam",
          description: "buy now",
          status: "pending",
          created_at: "2026-01-01T00:00:00Z",
        },
        {
          id: "r2",
          reporter_id: "u2",
          target_type: "comment",
          target_id: "c1",
          reason: "harassment",
          description: null,
          status: "pending",
          created_at: "2026-01-02T00:00:00Z",
        },
      ],
    },
  }),
  useReportAction: () => ({ mutateAsync: act, isPending: false }),
}));

describe("ModerationQueue", () => {
  it("lists pending reports", () => {
    render(<ModerationQueue />);
    expect(screen.getByText("spam")).toBeInTheDocument();
    expect(screen.getByText("harassment")).toBeInTheDocument();
  });

  it("expands a report to show full details", async () => {
    const user = userEvent.setup();
    render(<ModerationQueue />);
    await user.click(screen.getByRole("button", { name: "Expand report r1" }));
    expect(screen.getByText("buy now", { selector: "p" })).toBeInTheDocument();
  });

  it("applies one action to all selected reports", async () => {
    const user = userEvent.setup();
    render(<ModerationQueue />);
    await user.click(screen.getByRole("checkbox", { name: "Select r1" }));
    await user.click(screen.getByRole("checkbox", { name: "Select r2" }));
    await user.click(screen.getByRole("button", { name: "Dismiss selected" }));
    await waitFor(() => expect(act).toHaveBeenCalledTimes(2));
    expect(act).toHaveBeenCalledWith(
      expect.objectContaining({ id: "r1", action: "dismiss" }),
    );
  });
});
