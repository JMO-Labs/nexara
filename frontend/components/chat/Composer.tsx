'use client';
/**
 * @file components/chat/Composer.tsx
 * @brief Sticky-bottom chat composer. Multiline textarea + media controls
 *        (emoji, attach, poll). Enter sends, Shift+Enter inserts newline.
 *        Typing frames debounced by caller via onTyping.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import {
  PaperAirplaneIcon,
  PhotoIcon,
  FaceSmileIcon,
  ChartBarIcon,
  XMarkIcon,
  ArrowUturnLeftIcon,
} from '@heroicons/react/24/outline';
import { Textarea, IconButton } from '@/components/ui';

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
const QUICK_EMOJI = ['👍', '❤️', '🎉', '😂', '🤔', '🔥', '✨', '👀'];

export function Composer({
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
}: ComposerProps) {
  const [value, setValue] = React.useState('');
  const [emojiOpen, setEmojiOpen] = React.useState(false);
  const lastTyping = React.useRef(0);
  const taRef = React.useRef<HTMLTextAreaElement | null>(null);

  const submit = () => {
    const content = value.trim();
    if (!content || disabled) return;
    onSend(content);
    setValue('');
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    if (!onTyping) return;
    const now = Date.now();
    if (now - lastTyping.current > TYPING_DEBOUNCE_MS) {
      lastTyping.current = now;
      onTyping();
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
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
    <Box
      sx={{
        flexShrink: 0,
        bgcolor: 'background.surface',
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      {replyTo && (
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{
            px: 1.5,
            py: 0.75,
            bgcolor: 'background.level1',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <ArrowUturnLeftIcon width={14} />
          <Typography level="body-xs" sx={{ flex: 1, minWidth: 0 }} noWrap>
            <strong>Replying to {replyTo.authorName}:</strong> {replyTo.excerpt}
          </Typography>
          <IconButton
            size="sm"
            variant="plain"
            aria-label="Cancel reply"
            onClick={onCancelReply}
          >
            <XMarkIcon width={14} />
          </IconButton>
        </Stack>
      )}
      {emojiOpen && (
        <Stack
          direction="row"
          spacing={0.5}
          sx={{
            px: 1.5,
            py: 1,
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {QUICK_EMOJI.map((e) => (
            <IconButton
              key={e}
              variant="plain"
              size="sm"
              onClick={() => insertEmoji(e)}
              aria-label={`Insert ${e}`}
            >
              <span style={{ fontSize: 18 }}>{e}</span>
            </IconButton>
          ))}
        </Stack>
      )}

      <Stack direction="row" spacing={1} alignItems="flex-end" sx={{ p: 1.5 }}>
        <Stack direction="row" spacing={0.25}>
          <IconButton
            tooltip="Emoji"
            aria-label="Add emoji"
            variant="plain"
            size="sm"
            disabled={disabled}
            onClick={() => setEmojiOpen((v) => !v)}
          >
            <FaceSmileIcon width={18} />
          </IconButton>
          <IconButton
            tooltip="Attach media"
            aria-label="Attach media"
            variant="plain"
            size="sm"
            disabled={disabled || !onAttachMedia}
            onClick={onAttachMedia}
          >
            <PhotoIcon width={18} />
          </IconButton>
          <IconButton
            tooltip="Create poll"
            aria-label="Create poll"
            variant="plain"
            size="sm"
            disabled={disabled || !onCreatePoll}
            onClick={onCreatePoll}
          >
            <ChartBarIcon width={18} />
          </IconButton>
        </Stack>

        <Textarea
          slotProps={{ textarea: { ref: taRef } }}
          minRows={1}
          maxRows={6}
          value={value}
          onChange={handleChange}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder={placeholder ?? 'Write a message…'}
          sx={{ flex: 1 }}
        />

        <IconButton
          tooltip="Send"
          shortcut="Enter"
          aria-label="Send message"
          onClick={submit}
          disabled={disabled || !value.trim()}
          variant="solid"
          color="primary"
        >
          <PaperAirplaneIcon width={18} />
        </IconButton>
      </Stack>

      {connectionLabel && (
        <Typography
          level="body-xs"
          textColor="text.tertiary"
          sx={{ px: 2, pb: 1 }}
        >
          {connectionLabel}
        </Typography>
      )}
    </Box>
  );
}
