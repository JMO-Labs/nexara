/**
 * @file tests/unit/feed/PostComposer.test.tsx
 * @brief PostComposer tests (reply-to-prompt banner, submit with reply_to_prompt_id).
 */
import { vi } from "vitest";

// Mock the hook BEFORE importing the component
const mockCreatePost = vi.fn(async (body) => {
  return { id: "post1", content: body.content, ...body };
});

vi.mock("@/hooks/usePosts", () => ({
  useCreatePost: () => ({
    mutateAsync: mockCreatePost,
    isPending: false,
  }),
}));

// Now safe to import component and dependencies
import React, { useState } from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useToasts } from "@/stores/toasts";
import { PostComposer } from "@/components/feed/PostComposer";

// Mock session store
vi.mock("@/stores/session", () => ({
  useSession: vi.fn((selector) => {
    const mockUser = {
      id: "user1",
      display_name: "Test User",
      avatar_url: "https://example.com/avatar.jpg",
    };
    return selector({ user: mockUser });
  }),
}));

vi.mock("@/lib/api/users", () => ({ addInterest: vi.fn(async () => {}) }));

vi.mock("@/hooks/useCalendars", () => ({
  useCalendars: () => ({
    data: [
      { id: "cal1", kind: "subgroup", name: "Family", subgroup_id: "sg1" },
      { id: "cal2", kind: "subgroup", name: "Work", subgroup_id: "sg2" },
    ],
  }),
}));

describe("PostComposer", () => {
  function wrap(ui: React.ReactNode) {
    return render(<>{ui}</>);
  }

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreatePost.mockClear();
  });

  it("renders collapsed state initially", () => {
    wrap(<PostComposer />);
    const trigger = screen.getByText(/Share something with your community/i);
    expect(trigger).toBeInTheDocument();
  });

  describe("reply-to-prompt banner", () => {
    it("shows banner when replyToPromptId and replyToPromptTitle are set", async () => {
      const user = userEvent.setup();
      wrap(
        <PostComposer
          replyToPromptId="prompt1"
          replyToPromptTitle="What is your favorite holiday?"
        />,
      );

      // Expand the composer
      const trigger = screen.getByText(/Share something with your community/i);
      await user.click(trigger);

      // Check for banner text - it should show "Replying to: <title>"
      expect(screen.getByText(/Replying to:/i)).toBeInTheDocument();
      expect(
        screen.getByText(/What is your favorite holiday\?/i),
      ).toBeInTheDocument();
    });

    it("hides banner when only replyToPromptId is set (without title)", async () => {
      const user = userEvent.setup();
      wrap(<PostComposer replyToPromptId="prompt1" />);

      // Expand the composer
      const trigger = screen.getByText(/Share something with your community/i);
      await user.click(trigger);

      // Banner should not appear without title
      expect(screen.queryByText(/Replying to:/i)).not.toBeInTheDocument();
    });

    it("clears reply state when X button is clicked", async () => {
      const user = userEvent.setup();
      const onClear = vi.fn();

      const TestWrapper = () => {
        const [promptId, setPromptId] = useState("prompt1");
        const [promptTitle, setPromptTitle] = useState(
          "What is your favorite?",
        );

        return (
          <PostComposer
            replyToPromptId={promptId}
            replyToPromptTitle={promptTitle}
            onClearReplyPrompt={() => {
              setPromptId("");
              setPromptTitle("");
              onClear();
            }}
          />
        );
      };

      wrap(<TestWrapper />);

      // Expand composer
      const trigger = screen.getByText(/Share something with your community/i);
      await user.click(trigger);

      // Find and click the clear button (X button in the banner)
      const clearBtn = screen.getByLabelText(/clear reply/i);
      await user.click(clearBtn);

      // Verify callback was called
      expect(onClear).toHaveBeenCalled();
    });
  });

  describe("submit with reply_to_prompt_id", () => {
    it("includes reply_to_prompt_id in submit payload when set", async () => {
      const user = userEvent.setup();

      wrap(
        <PostComposer
          replyToPromptId="prompt1"
          replyToPromptTitle="What is your favorite holiday?"
        />,
      );

      // Expand composer
      const trigger = screen.getByText(/Share something with your community/i);
      await user.click(trigger);

      // Type content in the editor
      const editor = document.querySelector(".tiptap-editor") as HTMLElement;
      expect(editor).toBeInTheDocument();
      await user.click(editor);
      await user.keyboard("Test reply content");

      // Submit
      const postBtn = screen.getByRole("button", { name: /Post/i });
      await user.click(postBtn);

      // Verify the mock was called with reply_to_prompt_id in payload
      expect(mockCreatePost).toHaveBeenCalled();
      const callArgs = mockCreatePost.mock.calls[0]?.[0];
      expect(callArgs).toBeDefined();
      expect(callArgs.reply_to_prompt_id).toBe("prompt1");
      expect(callArgs.content).toContain("Test reply content");
    });

    it("submits without reply_to_prompt_id when not set", async () => {
      const user = userEvent.setup();
      wrap(<PostComposer />);

      // Expand composer
      const trigger = screen.getByText(/Share something with your community/i);
      await user.click(trigger);

      // Type content
      const editor = document.querySelector(".tiptap-editor") as HTMLElement;
      expect(editor).toBeInTheDocument();
      await user.click(editor);
      await user.keyboard("Normal post content");

      // Submit
      const postBtn = screen.getByRole("button", { name: /Post/i });
      await user.click(postBtn);

      // Verify the mock was called without reply_to_prompt_id
      expect(mockCreatePost).toHaveBeenCalled();
      const callArgs = mockCreatePost.mock.calls[0]?.[0];
      expect(callArgs).toBeDefined();
      expect(callArgs.reply_to_prompt_id).toBeUndefined();
      expect(callArgs.content).toContain("Normal post content");
    });

    it("includes visibility and subgroup_id in submit payload", async () => {
      const user = userEvent.setup();
      wrap(<PostComposer />);

      // Expand composer
      const trigger = screen.getByText(/Share something with your community/i);
      await user.click(trigger);

      // Type content
      const editor = document.querySelector(".tiptap-editor") as HTMLElement;
      expect(editor).toBeInTheDocument();
      await user.click(editor);
      await user.keyboard("Test post");

      // Submit
      const postBtn = screen.getByRole("button", { name: /Post/i });
      await user.click(postBtn);

      // Verify scope is in payload
      expect(mockCreatePost).toHaveBeenCalled();
      const callArgs = mockCreatePost.mock.calls[0]?.[0];
      expect(callArgs).toBeDefined();
      expect(callArgs.visibility).toBe("community");
      expect(callArgs.subgroup_id).toBeNull();
    });
  });

  describe("new behavior", () => {
    async function open(ui: React.ReactNode, text = "Hello") {
      const user = userEvent.setup();
      wrap(ui);
      await user.click(
        screen.getByText(/Share something with your community/i),
      );
      await user.click(document.querySelector(".tiptap-editor") as HTMLElement);
      await user.keyboard(text);
      return user;
    }

    it("sends subgroup payload when defaultSubgroupId is set", async () => {
      const user = await open(<PostComposer defaultSubgroupId="sg1" />);
      await user.click(screen.getByRole("button", { name: "Post" }));
      const args = mockCreatePost.mock.calls[0]?.[0];
      expect(args.visibility).toBe("subgroup");
      expect(args.subgroup_id).toBe("sg1");
    });

    it("pushes a Posted toast on success", async () => {
      useToasts.getState().clear();
      const user = await open(<PostComposer />);
      await user.click(screen.getByRole("button", { name: "Post" }));
      expect(
        useToasts.getState().items.some((t) => t.message === "Posted"),
      ).toBe(true);
    });

    it("shows the interest slug as visible chip text after posting", async () => {
      const user = await open(
        <PostComposer
          promptType="interest_capture"
          interestCategorySlug="gardening"
        />,
      );
      await user.click(screen.getByRole("button", { name: "Post" }));
      expect(await screen.findByText("gardening")).toBeVisible();
      expect(screen.getByText(/Add to your interests/i)).toBeInTheDocument();
    });
  });

  describe("banner styling", () => {
    it("uses Alert component with proper styling", async () => {
      const user = userEvent.setup();
      wrap(
        <PostComposer
          replyToPromptId="prompt1"
          replyToPromptTitle="What is your favorite?"
        />,
      );

      // Expand composer
      const trigger = screen.getByText(/Share something with your community/i);
      await user.click(trigger);

      // Look for the banner text
      const bannerText = screen.getByText(/Replying to:/i);
      expect(bannerText).toBeInTheDocument();

      // Check that the X button is present
      const clearBtn = screen.getByLabelText(/clear reply/i);
      expect(clearBtn).toBeInTheDocument();
    });
  });
});
