"use client";
/**
 * @file components/feed/PostComposer.tsx
 * @brief Tailwind/shadcn-skinned Tiptap-based rich-text composer for new posts. Inline trigger row
 *        opens an editor; supports submit on Cmd/Ctrl+Enter.
 *        Polls and media attachment surfaced as toggles; payload pieces
 *        are attached as media_ids / poll on submit.
 *        Supports reply-to-prompt with banner display and state management.
 *        Shows interest-capture prompt after submitting interest_capture replies.
 */
import * as React from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import {
  Avatar,
  Button,
  Chip,
  IconButton,
  ScopeSelect,
  type ScopeValue,
} from "@/components/ui";
import { useSession } from "@/stores/session";
import { useCreatePost } from "@/hooks/usePosts";
import { useCalendars } from "@/hooks/useCalendars";
import { addInterest } from "@/lib/api/users";
import { useToasts } from "@/stores/toasts";
import { ComposerToolbar } from "./ComposerToolbar";
import { X } from "lucide-react";

export interface PostComposerProps {
  onPosted?: () => void;
  replyToPromptId?: string;
  replyToPromptTitle?: string;
  onClearReplyPrompt?: () => void;
  promptType?: "standard" | "interest_capture";
  interestCategorySlug?: string;
  defaultSubgroupId?: string | null;
}

export function PostComposer({
  onPosted,
  replyToPromptId,
  replyToPromptTitle,
  onClearReplyPrompt,
  promptType = "standard",
  interestCategorySlug,
  defaultSubgroupId,
}: PostComposerProps) {
  const me = useSession((s) => s.user);
  const createMut = useCreatePost();
  const { data: calendars } = useCalendars();
  const [expanded, setExpanded] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [showInterest, setShowInterest] = React.useState(false);
  const [addingInterest, setAddingInterest] = React.useState(false);
  const [scope, setScope] = React.useState<ScopeValue>({
    visibility: defaultSubgroupId ? "subgroup" : "community",
    subgroup_id: defaultSubgroupId ?? null,
  });

  const myGroups = React.useMemo(
    () =>
      (calendars ?? [])
        .filter((c) => c.kind === "subgroup" && c.subgroup_id)
        .map((c) => ({ id: c.subgroup_id as string, name: c.name })),
    [calendars],
  );

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
      const payload: {
        content: string;
        reply_to_prompt_id?: string;
        visibility?: string;
        subgroup_id?: string | null;
      } = {
        content: text,
      };
      if (replyToPromptId) {
        payload.reply_to_prompt_id = replyToPromptId;
      }
      payload.visibility = scope.visibility;
      if (scope.visibility === "subgroup" && scope.subgroup_id) {
        payload.subgroup_id = scope.subgroup_id;
      } else {
        payload.subgroup_id = null;
      }
      await createMut.mutateAsync(payload);
      editor.commands.clearContent();
      setExpanded(false);
      useToasts.getState().push({ variant: "success", message: "Posted" });

      // Show interest toast if this is an interest_capture prompt reply
      if (promptType === "interest_capture" && interestCategorySlug) {
        setShowInterest(true);
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
    scope,
  ]);

  if (!me) return null;

  const interestPrompt = showInterest ? (
    <div
      role="status"
      className="bg-surface text-ink mt-2 flex flex-col items-start gap-2 rounded-2xl border border-muted/40 p-3"
    >
      <p className="text-sm font-semibold">Add to your interests?</p>
      {interestCategorySlug && (
        <Chip tone="accent">{interestCategorySlug}</Chip>
      )}
      <div className="flex gap-2">
        <Button
          size="sm"
          loading={addingInterest}
          onClick={async () => {
            if (!interestCategorySlug) return;
            setAddingInterest(true);
            try {
              await addInterest(interestCategorySlug);
              setShowInterest(false);
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
          variant="ghost"
          onClick={() => setShowInterest(false)}
        >
          Not now
        </Button>
      </div>
    </div>
  ) : null;

  if (!expanded) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="bg-surface text-muted focus-visible:outline-accent flex w-full cursor-text items-center gap-3 rounded-[1.25rem] border border-muted/40 p-3 text-left focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          <Avatar
            src={me.avatar_url ?? undefined}
            name={me.display_name}
            size="sm"
          />
          <span className="text-base">
            Share something with your community…
          </span>
        </button>
        {interestPrompt}
      </div>
    );
  }

  return (
    <div
      className="bg-surface rounded-[1.25rem] border border-muted/40 p-3"
      data-tour="composer"
    >
      {replyToPromptId && replyToPromptTitle && (
        <div className="bg-bg mb-3 flex items-center justify-between gap-2 rounded-xl p-2 text-sm">
          <p>
            <strong>Replying to:</strong> {replyToPromptTitle}
          </p>
          <IconButton
            aria-label="Clear reply"
            variant="ghost"
            size="sm"
            onClick={onClearReplyPrompt}
          >
            <X className="size-4" aria-hidden />
          </IconButton>
        </div>
      )}

      <div className="flex items-start gap-3">
        <Avatar
          src={me.avatar_url ?? undefined}
          name={me.display_name}
          size="sm"
        />
        <div className="min-w-0 grow">
          <div className="min-h-20 rounded-xl border border-muted/40 p-2 [&_.tiptap-editor]:min-h-[60px] [&_.tiptap-editor]:outline-none [&_.tiptap-editor_p.is-editor-empty:first-of-type]:before:pointer-events-none [&_.tiptap-editor_p.is-editor-empty:first-of-type]:before:float-left [&_.tiptap-editor_p.is-editor-empty:first-of-type]:before:h-0 [&_.tiptap-editor_p.is-editor-empty:first-of-type]:before:text-muted [&_.tiptap-editor_p.is-editor-empty:first-of-type]:before:content-[attr(data-placeholder)]">
            <EditorContent editor={editor} />
          </div>
          {error ? (
            <p role="alert" className="mt-1 text-xs text-destructive">
              {error}
            </p>
          ) : null}
          {!defaultSubgroupId && (
            <div className="mt-3 mb-2">
              <ScopeSelect
                value={scope}
                onChange={setScope}
                subgroups={myGroups}
              />
            </div>
          )}
          <ComposerToolbar
            posting={createMut.isPending}
            onSubmit={submit}
            onCancel={() => {
              editor?.commands.clearContent();
              setExpanded(false);
              setError(null);
            }}
          />
        </div>
      </div>
      {interestPrompt}
    </div>
  );
}

export default PostComposer;
