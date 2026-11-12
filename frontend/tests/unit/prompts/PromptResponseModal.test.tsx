/**
 * @file tests/unit/prompts/PromptResponseModal.test.tsx
 * @brief Response modal: text submit via createPost with reply_to_prompt_id.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { PromptResponseModal } from "@/components/prompts/PromptResponseModal";

const mutate = vi.fn();
vi.mock("@/hooks/usePosts", () => ({
  useCreatePost: () => ({ mutate, isPending: false }),
}));

describe("PromptResponseModal", () => {
  it("disables submit when empty", () => {
    render(
      <PromptResponseModal
        open
        onClose={vi.fn()}
        promptPostId="p1"
        title="T"
      />,
    );
    expect(screen.getByRole("button", { name: /submit/i })).toBeDisabled();
  });

  it("submits trimmed text with reply_to_prompt_id", async () => {
    const onClose = vi.fn();
    mutate.mockImplementation((_b, o) => o?.onSuccess?.());
    render(
      <PromptResponseModal
        open
        onClose={onClose}
        promptPostId="p1"
        title="T"
      />,
    );
    await userEvent.type(screen.getByRole("textbox"), "  Pancakes ");
    await userEvent.click(screen.getByRole("button", { name: /submit/i }));
    expect(mutate).toHaveBeenCalledWith(
      { content: "Pancakes", reply_to_prompt_id: "p1" },
      expect.anything(),
    );
    expect(onClose).toHaveBeenCalled();
  });
});
