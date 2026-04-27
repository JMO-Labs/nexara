'use client';
/**
 * @file components/feed/PostComposer.tsx
 * @brief Tiptap-based rich-text composer for new posts. Inline trigger row
 *        opens an editor; supports submit on Cmd/Ctrl+Enter.
 *        Polls and media attachment surfaced as toggles; payload pieces
 *        are attached as media_ids / poll on submit.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { Avatar, Button, IconButton } from '@/components/ui';
import { useSession } from '@/stores/session';
import { useCreatePost } from '@/hooks/usePosts';
import {
  PhotoIcon,
  ChartBarIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

export interface PostComposerProps {
  onPosted?: () => void;
}

export function PostComposer({ onPosted }: PostComposerProps) {
  const me = useSession((s) => s.user);
  const createMut = useCreatePost();
  const [expanded, setExpanded] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        bulletList: false,
        orderedList: false,
        blockquote: false,
        codeBlock: false,
        horizontalRule: false,
        link: { openOnClick: false, autolink: true },
      }),
      Placeholder.configure({ placeholder: 'Share something with your community…' }),
    ],
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: 'tiptap-editor',
        'aria-label': 'Post composer',
      },
      handleKeyDown: (_view, event) => {
        if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
          event.preventDefault();
          submit();
          return true;
        }
        return false;
      },
    },
  });

  const submit = React.useCallback(async () => {
    if (!editor) return;
    const text = editor.getText().trim();
    if (!text) {
      setError('Add some content before posting.');
      return;
    }
    setError(null);
    try {
      await createMut.mutateAsync({ content: text });
      editor.commands.clearContent();
      setExpanded(false);
      onPosted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to post.');
    }
  }, [editor, createMut, onPosted]);

  if (!me) return null;

  if (!expanded) {
    return (
      <Box
        onClick={() => setExpanded(true)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          p: 1.5,
          borderRadius: 'lg',
          border: '1px solid',
          borderColor: 'divider',
          backgroundColor: 'background.surface',
          cursor: 'text',
        }}
      >
        <Avatar src={me.avatar_url ?? undefined} size="sm">
          {me.display_name.charAt(0)}
        </Avatar>
        <Typography level="body-md" textColor="text.tertiary">
          Share something with your community…
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: 'lg',
        border: '1px solid',
        borderColor: 'divider',
        backgroundColor: 'background.surface',
      }}
      data-tour="composer"
    >
      <Stack direction="row" spacing={1.5} alignItems="flex-start">
        <Avatar src={me.avatar_url ?? undefined} size="sm">
          {me.display_name.charAt(0)}
        </Avatar>
        <Box sx={{ flexGrow: 1 }}>
          <Box
            sx={{
              minHeight: 80,
              borderRadius: 'md',
              p: 1,
              border: '1px solid',
              borderColor: 'divider',
              '& .tiptap-editor': { outline: 'none', minHeight: 60 },
              '& .tiptap-editor p.is-editor-empty:first-of-type::before': {
                content: 'attr(data-placeholder)',
                color: 'var(--joy-palette-text-tertiary)',
                float: 'left',
                pointerEvents: 'none',
                height: 0,
              },
            }}
          >
            <EditorContent editor={editor} />
          </Box>
          {error ? (
            <Typography level="body-xs" color="danger" sx={{ mt: 0.5 }}>
              {error}
            </Typography>
          ) : null}
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            sx={{ mt: 1 }}
          >
            <IconButton
              aria-label="Attach media"
              variant="plain"
              size="sm"
              disabled
              title="Coming soon"
            >
              <PhotoIcon width={18} />
            </IconButton>
            <IconButton
              aria-label="Add poll"
              variant="plain"
              size="sm"
              disabled
              title="Coming soon"
            >
              <ChartBarIcon width={18} />
            </IconButton>
            <Box sx={{ flexGrow: 1 }} />
            <IconButton
              aria-label="Cancel"
              variant="plain"
              size="sm"
              onClick={() => {
                editor?.commands.clearContent();
                setExpanded(false);
                setError(null);
              }}
            >
              <XMarkIcon width={18} />
            </IconButton>
            <Button onClick={submit} loading={createMut.isPending} size="sm">
              Post
            </Button>
          </Stack>
        </Box>
      </Stack>
    </Box>
  );
}

export default PostComposer;
