"use client";
/**
 * @file components/prompts/PromptResponseModal.tsx
 * @brief Modal to submit a text response to a prompt post.
 */
import * as React from "react";
import { Button, Modal, Textarea } from "@/components/ui";
import { useCreatePost } from "@/hooks/usePosts";

export interface PromptResponseModalProps {
  open: boolean;
  onClose: () => void;
  promptPostId: string;
  title: string;
}

/**
 * @brief Response modal; submits a post with reply_to_prompt_id.
 * @param props see PromptResponseModalProps
 * @return modal element
 */
export function PromptResponseModal({
  open,
  onClose,
  promptPostId,
  title,
}: PromptResponseModalProps) {
  const [text, setText] = React.useState("");
  const create = useCreatePost();
  const content = text.trim();

  const submit = () =>
    create.mutate(
      { content, reply_to_prompt_id: promptPostId },
      {
        onSuccess: () => {
          setText("");
          onClose();
        },
      },
    );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Respond"
      description={title}
      footer={
        <Button
          onClick={submit}
          disabled={!content || create.isPending}
          className="min-h-11"
        >
          Submit
        </Button>
      }
    >
      <Textarea
        label="Your response"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={5}
      />
    </Modal>
  );
}

export default PromptResponseModal;
