"use client";
/**
 * @file components/chat/Composer.tsx
 * @brief Sticky-bottom chat composer. Multiline textarea + media controls
 *        (emoji, attach, poll). Enter / Ctrl+Enter send, Shift+Enter inserts newline.
 *        Typing frames debounced by caller via onTyping.
 */
import * as React from "react";
import {
  Send,
  Image as ImageIcon,
  Smile,
  BarChart3,
  X,
  CornerUpLeft,
} from "lucide-react";
import { IconButton } from "@/components/ui";
import { MentionMenu } from "@/components/mentions/MentionMenu";
import { useMentionInput } from "@/components/mentions/useMentionInput";

export interface ReplyContext {
  authorName: string;
  excerpt: string;
}

export interface ComposerProps {
  disabled?: boolean;
  connectionLabel?: string;
  onSend: (content: string) => void;
  onTyping?: () => void;
  onAttachMedia?: () => void;
  onAddEmoji?: (emoji: string) => void;
  onCreatePoll?: () => void;
  placeholder?: string;
  replyTo?: ReplyContext | null;
  onCancelReply?: () => void;
}

const TYPING_DEBOUNCE_MS = 1500;
const QUICK_EMOJI = ["👍", "❤️", "🎉", "😂", "🤔", "🔥", "✨", "👀"];

export interface ComposerHandle {
  /** Move focus into the message textarea. */
  focus: () => void;
}

export const Composer = React.forwardRef<ComposerHandle, ComposerProps>(
  function Composer(
    {
      disabled,
      connectionLabel,
      onSend,
      onTyping,
      onAttachMedia,
      onAddEmoji,
      onCreatePoll,
      placeholder,
      replyTo,
      onCancelReply,
    },
    ref,
  ) {
    const [value, setValue] = React.useState("");
    const [emojiOpen, setEmojiOpen] = React.useState(false);
    const lastTyping = React.useRef(0);
    const taRef = React.useRef<HTMLTextAreaElement | null>(null);
    const mention = useMentionInput(value, setValue, taRef);

    React.useImperativeHandle(
      ref,
      () => ({ focus: () => taRef.current?.focus() }),
      [],
    );

    const submit = () => {
      const content = value.trim();
      if (!content || disabled) return;
      onSend(content);
      setValue("");
    };

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      mention.onTextChange(e);
      if (!onTyping) return;
      const now = Date.now();
      if (now - lastTyping.current > TYPING_DEBOUNCE_MS) {
        lastTyping.current = now;
        onTyping();
      }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (mention.onKeyDown(e)) return;
      // Enter, Ctrl+Enter and Cmd+Enter send; Shift+Enter inserts a newline.
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    };

    const insertEmoji = (emoji: string) => {
      setValue((v) => v + emoji);
      setEmojiOpen(false);
      onAddEmoji?.(emoji);
      requestAnimationFrame(() => taRef.current?.focus());
    };

    return (
      <div className="shrink-0 px-2.5 pb-2.5">
        {replyTo && (
          <div className="flex items-center gap-2 mb-1.5 rounded-[18px] bg-[var(--nx-bubble)] px-3 py-1.5">
            <CornerUpLeft size={14} aria-hidden />
            <p className="min-w-0 flex-1 truncate text-xs">
              <strong>Replying to {replyTo.authorName}:</strong>{" "}
              {replyTo.excerpt}
            </p>
            <IconButton
              size="sm"
              variant="ghost"
              aria-label="Cancel reply"
              tooltip="Cancel reply"
              onClick={onCancelReply}
            >
              <X size={14} aria-hidden />
            </IconButton>
          </div>
        )}
        {emojiOpen && (
          <div className="mb-1.5 flex gap-1 px-3 py-1">
            {QUICK_EMOJI.map((e) => (
              <IconButton
                key={e}
                variant="ghost"
                size="sm"
                onClick={() => insertEmoji(e)}
                aria-label={`Insert ${e}`}
              >
                <span className="text-lg">{e}</span>
              </IconButton>
            ))}
          </div>
        )}

        <div className="relative flex items-end gap-2 rounded-[26px] bg-[var(--nx-glass-solid)] py-1.5 pl-2 pr-1.5">
          {mention.open && (
            <MentionMenu
              {...mention.menu}
              className="absolute bottom-full left-2 mb-2"
            />
          )}
          <div className="flex gap-0.5">
            <IconButton
              aria-label="Add emoji"
              tooltip="Add emoji"
              variant="ghost"
              size="sm"
              disabled={disabled}
              onClick={() => setEmojiOpen((v) => !v)}
            >
              <Smile size={18} aria-hidden />
            </IconButton>
            <IconButton
              aria-label="Attach media"
              tooltip="Attach media"
              variant="ghost"
              size="sm"
              disabled={disabled || !onAttachMedia}
              onClick={onAttachMedia}
            >
              <ImageIcon size={18} aria-hidden />
            </IconButton>
            <IconButton
              aria-label="Create poll"
              tooltip="Create poll"
              variant="ghost"
              size="sm"
              disabled={disabled || !onCreatePoll}
              onClick={onCreatePoll}
            >
              <BarChart3 size={18} aria-hidden />
            </IconButton>
          </div>

          <textarea
            ref={taRef}
            rows={1}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            aria-label="Message"
            aria-autocomplete="list"
            placeholder={placeholder ?? "Write a message…"}
            {...mention.fieldProps}
            className="max-h-36 min-h-9 flex-1 resize-none bg-transparent px-2 py-2 text-[13.5px] outline-none placeholder:text-muted disabled:opacity-50"
          />

          <IconButton
            aria-label="Send message"
            tooltip="Send message"
            shortcut="Enter"
            onClick={submit}
            disabled={disabled || !value.trim()}
            className="bg-surface-strong text-bg disabled:opacity-40"
          >
            <Send size={18} aria-hidden />
          </IconButton>
        </div>

        {connectionLabel && (
          <p className="px-4 pb-2 text-xs text-muted">{connectionLabel}</p>
        )}
      </div>
    );
  },
);
