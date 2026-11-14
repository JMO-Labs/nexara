/**
 * @file tests/unit/moderation/ReportDialog.test.tsx
 * @brief ReportDialog / ReportButton / BlockButton behaviour.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportDialog } from "@/components/moderation/ReportDialog";
import { ReportButton } from "@/components/common/ReportButton";
import { BlockButton } from "@/components/common/BlockButton";

const submit = vi.fn();
const block = vi.fn();
const confirm = vi.fn();
const push = vi.fn();
vi.mock("@/lib/api/moderation", () => ({
  createReport: (...a: unknown[]) => submit(...a),
  blockUser: (...a: unknown[]) => block(...a),
}));
vi.mock("@/stores/confirmDialog", () => ({
  useConfirmDialog: Object.assign(() => ({}), {
    getState: () => ({ confirm }),
  }),
}));
vi.mock("@/stores/toasts", () => ({
  useToasts: (sel: (s: { push: typeof push }) => unknown) => sel({ push }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  submit.mockResolvedValue({ id: "r1" });
  block.mockResolvedValue({ id: "b1" });
});

describe("ReportDialog", () => {
  it("submits reason + details, toasts and closes", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <ReportDialog open onClose={onClose} targetType="post" targetId="p1" />,
    );
    await user.click(screen.getByRole("combobox", { name: "Reason" }));
    await user.click(await screen.findByRole("option", { name: "Spam" }));
    await user.type(screen.getByLabelText("Details (optional)"), "bad");
    await user.click(screen.getByRole("button", { name: "Submit report" }));
    await waitFor(() =>
      expect(submit).toHaveBeenCalledWith({
        target_type: "post",
        target_id: "p1",
        reason: "spam",
        description: "bad",
      }),
    );
    expect(push).toHaveBeenCalledWith(
      expect.objectContaining({ variant: "success" }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("disables submit until a reason is chosen", () => {
    render(
      <ReportDialog open onClose={vi.fn()} targetType="post" targetId="p1" />,
    );
    expect(
      screen.getByRole("button", { name: "Submit report" }),
    ).toBeDisabled();
  });
});

describe("ReportButton", () => {
  it("opens the dialog", async () => {
    const user = userEvent.setup();
    render(<ReportButton targetType="comment" targetId="c1" />);
    await user.click(screen.getByRole("button", { name: "Report" }));
    expect(await screen.findByText("Report content")).toBeInTheDocument();
  });
});

describe("BlockButton", () => {
  it("blocks only after confirmation", async () => {
    const user = userEvent.setup();
    confirm.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<BlockButton userId="u2" displayName="Bob" />);
    await user.click(screen.getByRole("button", { name: "Block Bob" }));
    expect(block).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Block Bob" }));
    await waitFor(() => expect(block).toHaveBeenCalledWith("u2"));
  });
});
