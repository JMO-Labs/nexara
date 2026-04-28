"use client";
/**
 * @file components/feed/PostComposer.tsx
 * @brief Tiptap-based rich-text composer for new posts. Inline trigger row
 *        opens an editor; supports submit on Cmd/Ctrl+Enter.
 *        Polls and media attachment surfaced as toggles; payload pieces
 *        are attached as media_ids / poll on submit.
 *        Supports reply-to-prompt with banner display and state management.
 *        Shows interest-capture toast after submitting interest_capture replies.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Box from "@mui/joy/Box";
import Alert from "@mui/joy/Alert";
import Typography from "@mui/joy/Typography";
import Snackbar from "@mui/joy/Snackbar";
import Chip from "@mui/joy/Chip";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { Avatar, Button, IconButton } from "@/components/ui";
import { useSession } from "@/stores/session";
import { useCreatePost } from "@/hooks/usePosts";
import { addInterest } from "@/lib/api/users";
import {
  PhotoIcon,
  ChartBarIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

export interface PostComposerProps {
  onPosted?: () => void;
  replyToPromptId?: string;
  replyToPromptTitle?: string;
  onClearReplyPrompt?: () => void;
  promptType?: "standard" | "interest_capture";
  interestCategorySlug?: string;
}

export function PostComposer({
  onPosted,
  replyToPromptId,
  replyToPromptTitle,
  onClearReplyPrompt,
  promptType = "standard",
  interestCategorySlug,
}: PostComposerProps) {
  const me = useSession((s) => s.user);
  const createMut = useCreatePost();
  const [expanded, setExpanded] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [showInterestToast, setShowInterestToast] = React.useState(false);
  const [addingInterest, setAddingInterest] = React.useState(false);

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
      Placeholder.configure({
        placeholder: "Share something with your community…",
      }),
    ],
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "tiptap-editor",
        "aria-label": "Post composer",
      },
      handleKeyDown: (_view, event) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
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
      setError("Add some content before posting.");
      return;
    }
    setError(null);
    try {
      const payload: { content: string; reply_to_prompt_id?: string } = {
        content: text,
      };
      if (replyToPromptId) {
        payload.reply_to_prompt_id = replyToPromptId;
      }
      await createMut.mutateAsync(payload);
      editor.commands.clearContent();
      setExpanded(false);

      // Show interest toast if this is an interest_capture prompt reply
      if (promptType === "interest_capture" && interestCategorySlug) {
        setShowInterestToast(true);
      }

      onPosted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to post.");
    }
  }, [
    editor,
    createMut,
    onPosted,
    replyToPromptId,
    promptType,
    interestCategorySlug,
  ]);

  if (!me) return null;

  if (!expanded) {
    return (
      <Box
        onClick={() => setExpanded(true)}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          p: 1.5,
          borderRadius: "lg",
          border: "1px solid",
          borderColor: "divider",
          backgroundColor: "background.surface",
          cursor: "text",
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
        borderRadius: "lg",
        border: "1px solid",
        borderColor: "divider",
        backgroundColor: "background.surface",
      }}
      data-tour="composer"
    >
      {/* Reply-to-prompt banner */}
      {replyToPromptId && replyToPromptTitle && (
        <Box
          sx={{
            mb: 1.5,
            animation: "fadeIn 0.3s ease-out",
            "@keyframes fadeIn": {
              from: { opacity: 0, transform: "translateY(-4px)" },
              to: { opacity: 1, transform: "translateY(0)" },
            },
          }}
        >
          <Alert
            variant="soft"
            color="primary"
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{ flexGrow: 1 }}
            >
              <Typography level="body-sm">
                <strong>Replying to:</strong> {replyToPromptTitle}
              </Typography>
            </Stack>
            <IconButton
              aria-label="Clear reply"
              variant="plain"
              size="sm"
              onClick={onClearReplyPrompt}
              sx={{ ml: 1 }}
            >
              <XMarkIcon width={16} />
            </IconButton>
          </Alert>
        </Box>
      )}

      <Stack direction="row" spacing={1.5} alignItems="flex-start">
        <Avatar src={me.avatar_url ?? undefined} size="sm">
          {me.display_name.charAt(0)}
        </Avatar>
        <Box sx={{ flexGrow: 1 }}>
          <Box
            sx={{
              minHeight: 80,
              borderRadius: "md",
              p: 1,
              border: "1px solid",
              borderColor: "divider",
              "& .tiptap-editor": { outline: "none", minHeight: 60 },
              "& .tiptap-editor p.is-editor-empty:first-of-type::before": {
                content: "attr(data-placeholder)",
                color: "var(--joy-palette-text-tertiary)",
                float: "left",
                pointerEvents: "none",
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
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
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

      {/* Interest-capture toast */}
      <Snackbar
        variant="soft"
        color="primary"
        open={showInterestToast}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        onClose={() => setShowInterestToast(false)}
        sx={{ zIndex: 1000 }}
      >
        <Stack direction="column" spacing={1}>
          <Typography level="body-sm">
            <strong>Add to your interests?</strong>
          </Typography>
          {interestCategorySlug && (
            <Chip
              size="sm"
              variant="soft"
              color="primary"
              label={interestCategorySlug}
              sx={{ alignSelf: "flex-start" }}
            />
          )}
          <Stack direction="row" spacing={1}>
            <Button
              size="sm"
              variant="solid"
              color="primary"
              loading={addingInterest}
              onClick={async () => {
                if (!interestCategorySlug) return;
                setAddingInterest(true);
                try {
                  await addInterest(interestCategorySlug);
                  setShowInterestToast(false);
                } catch (e) {
                  console.error("Failed to add interest:", e);
                } finally {
                  setAddingInterest(false);
                }
              }}
            >
              Add
            </Button>
            <Button
              size="sm"
              variant="plain"
              color="neutral"
              onClick={() => setShowInterestToast(false)}
            >
              Not now
            </Button>
          </Stack>
        </Stack>
      </Snackbar>
    </Box>
  );
}

export default PostComposer;
