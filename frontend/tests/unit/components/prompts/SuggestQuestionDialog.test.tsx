/**
 * @file tests/unit/components/prompts/SuggestQuestionDialog.test.tsx
 * @brief Submit calls the API and toasts; 429 shows the daily-limit message.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ApiError } from "@/lib/api/errors";

const m = vi.hoisted(() => ({ suggest: vi.fn(), push: vi.fn() }));
vi.mock("@/lib/api/dailyQuestions", () => ({ suggestQuestion: m.suggest }));
vi.mock("@/stores/toasts", () => ({
  useToasts: (sel: (s: { push: typeof m.push }) => unknown) =>
    sel({ push: m.push }),
}));

import { SuggestQuestionDialog } from "@/components/prompts/SuggestQuestionDialog";

async function open() {
  const user = userEvent.setup();
  render(<SuggestQuestionDialog />);
  await user.click(screen.getByRole("button", { name: "Suggest a question" }));
  await user.type(screen.getByLabelText("Your question"), "Best trip?");
  return user;
}

beforeEach(() => vi.clearAllMocks());

describe("SuggestQuestionDialog", () => {
  it("submits, toasts and shows char count", async () => {
    m.suggest.mockResolvedValue({});
    const user = await open();
    expect(screen.getByText("10/280")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(m.suggest).toHaveBeenCalledWith("Best trip?"));
    expect(m.push).toHaveBeenCalledWith({
      variant: "success",
      message: "Thanks — an admin will review it",
    });
  });

  it("shows the limit message on 429", async () => {
    m.suggest.mockRejectedValue(new ApiError(429, "RATE_LIMITED", "x"));
    const user = await open();
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(
      await screen.findByText("You can suggest 3 questions a day"),
    ).toBeTruthy();
    expect(m.push).not.toHaveBeenCalled();
  });
});
