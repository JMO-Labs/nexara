/**
 * @file tests/unit/moderation/ModerationQueue.test.tsx
 * @brief Admin moderation queue table, expand and batch actions.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModerationQueue } from "@/components/moderation/ModerationQueue";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useToasts } from "@/stores/toasts";

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

const confirm = vi.fn();

async function pickRowAction(name: string) {
  const user = userEvent.setup();
  render(<ModerationQueue />);
  await user.click(screen.getByRole("combobox", { name: "Action for r1" }));
  await user.click(await screen.findByRole("option", { name }));
}

describe("ModerationQueue", () => {
  beforeEach(() => {
    act.mockReset().mockResolvedValue({});
    confirm.mockReset().mockResolvedValue(true);
    useConfirmDialog.setState({ confirm } as never);
    useToasts.getState().clear();
  });

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

  it("asks for confirmation before a destructive row action", async () => {
    confirm.mockResolvedValue(false);
    await pickRowAction("Delete");
    await waitFor(() => expect(confirm).toHaveBeenCalled());
    expect(act).not.toHaveBeenCalled();
  });

  it("runs the row action after confirm", async () => {
    await pickRowAction("Ban");
    await waitFor(() =>
      expect(act).toHaveBeenCalledWith(
        expect.objectContaining({ id: "r1", action: "ban_user" }),
      ),
    );
  });

  it("does not confirm non-destructive row actions", async () => {
    await pickRowAction("Warn");
    await waitFor(() => expect(act).toHaveBeenCalled());
    expect(confirm).not.toHaveBeenCalled();
  });

  it("toasts when a row action fails", async () => {
    act.mockRejectedValue(new Error("boom"));
    await pickRowAction("Hide");
    await waitFor(() =>
      expect(useToasts.getState().items[0]).toMatchObject({
        variant: "danger",
      }),
    );
  });

  it("toasts when a batch action fails", async () => {
    act.mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    render(<ModerationQueue />);
    await user.click(screen.getByRole("checkbox", { name: "Select r1" }));
    await user.click(screen.getByRole("button", { name: "Dismiss selected" }));
    await waitFor(() =>
      expect(useToasts.getState().items[0]).toMatchObject({
        variant: "danger",
      }),
    );
  });
});
