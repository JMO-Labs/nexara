"use client";
/**
 * @file components/feed/ComposerAttachments.tsx
 * @brief Composer add-ons: poll editor and photo tray (upload + wait until the
 *        thumbnail job marks media ready, since posts reject unready media).
 */
import * as React from "react";
import { Loader2, Plus, X } from "lucide-react";
import { IconButton } from "@/components/ui";
import { getMedia, singleUpload } from "@/lib/api/media";

export interface PollDraft {
  question: string;
  options: string[];
  multiple: boolean;
}

export const emptyPoll = (): PollDraft => ({
  question: "",
  options: ["", ""],
  multiple: false,
});

/**
 * @brief Poll draft -> CreatePostBody.poll, or an error message.
 * @param d draft
 * @return payload or error string
 */
export function pollPayload(d: PollDraft) {
  const options = d.options.map((o) => o.trim()).filter(Boolean);
  if (!d.question.trim()) return "Add a poll question.";
  if (options.length < 2) return "A poll needs at least two options.";
  return {
    question: d.question.trim(),
    poll_type: d.multiple ? ("multiple" as const) : ("single" as const),
    options: options.map((label) => ({ label })),
  };
}

const field =
  "w-full rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] px-4 py-2 text-sm outline-none placeholder:text-muted focus-visible:outline-2 focus-visible:outline-accent";

/**
 * @brief Inline poll editor.
 * @param value draft
 * @param onChange update
 * @param onRemove drop the poll
 * @return editor
 */
export function PollEditor({
  value,
  onChange,
  onRemove,
}: {
  value: PollDraft;
  onChange: (d: PollDraft) => void;
  onRemove: () => void;
}) {
  const setOpt = (i: number, v: string) =>
    onChange({
      ...value,
      options: value.options.map((o, j) => (j === i ? v : o)),
    });
  return (
    <div className="mt-2 flex flex-col gap-2 rounded-[20px] p-1">
      <div className="flex items-center gap-2">
        <input
          aria-label="Poll question"
          placeholder="Ask a question"
          maxLength={500}
          className={field}
          value={value.question}
          onChange={(e) => onChange({ ...value, question: e.target.value })}
        />
        <IconButton
          aria-label="Remove poll"
          variant="ghost"
          size="sm"
          onClick={onRemove}
        >
          <X className="size-4" aria-hidden />
        </IconButton>
      </div>
      {value.options.map((o, i) => (
        <div key={i} className="flex items-center gap-2 pl-4">
          <input
            aria-label={`Option ${i + 1}`}
            placeholder={`Option ${i + 1}`}
            maxLength={200}
            className={field}
            value={o}
            onChange={(e) => setOpt(i, e.target.value)}
          />
          {value.options.length > 2 && (
            <IconButton
              aria-label={`Remove option ${i + 1}`}
              variant="ghost"
              size="sm"
              onClick={() =>
                onChange({
                  ...value,
                  options: value.options.filter((_, j) => j !== i),
                })
              }
            >
              <X className="size-4" aria-hidden />
            </IconButton>
          )}
        </div>
      ))}
      <div className="flex items-center gap-4 pl-4 text-sm">
        {value.options.length < 10 && (
          <button
            type="button"
            className="flex items-center gap-1 text-muted hover:text-ink"
            onClick={() =>
              onChange({ ...value, options: [...value.options, ""] })
            }
          >
            <Plus className="size-4" aria-hidden /> Add option
          </button>
        )}
        <label className="flex items-center gap-2 text-muted">
          <input
            type="checkbox"
            checked={value.multiple}
            onChange={(e) => onChange({ ...value, multiple: e.target.checked })}
          />
          Allow multiple answers
        </label>
      </div>
    </div>
  );
}

interface Upload {
  key: string;
  id?: string;
  preview: string;
  state: "uploading" | "ready" | "error";
}

/**
 * @brief Photo upload state for the composer.
 * @return uploads, add(files), remove(key), ready ids, busy flag, reset
 */
export function useMediaUploads() {
  const [items, setItems] = React.useState<Upload[]>([]);
  const patch = (key: string, p: Partial<Upload>) =>
    setItems((xs) => xs.map((x) => (x.key === key ? { ...x, ...p } : x)));

  const add = (files: FileList | null) => {
    for (const file of Array.from(files ?? [])) {
      const key = crypto.randomUUID();
      setItems((xs) => [
        ...xs,
        { key, preview: URL.createObjectURL(file), state: "uploading" },
      ]);
      void (async () => {
        try {
          const m = await singleUpload(file);
          patch(key, { id: m.id });
          // ponytail: poll ~30s for the thumbnail job; SSE if it ever lags.
          for (let i = 0; i < 30; i++) {
            const cur = i === 0 ? m : await getMedia(m.id);
            if (cur.status === "ready") return patch(key, { state: "ready" });
            if (cur.status === "error") break;
            await new Promise((r) => setTimeout(r, 1000));
          }
          patch(key, { state: "error" });
        } catch {
          patch(key, { state: "error" });
        }
      })();
    }
  };

  return {
    items,
    add,
    remove: (key: string) => setItems((xs) => xs.filter((x) => x.key !== key)),
    readyIds: items.filter((x) => x.state === "ready").map((x) => x.id!),
    busy: items.some((x) => x.state === "uploading"),
    reset: () => setItems([]),
  };
}

/**
 * @brief Thumbnails of attached photos.
 * @param items uploads
 * @param onRemove remove handler
 * @return tray or null
 */
export function MediaTray({
  items,
  onRemove,
}: {
  items: Upload[];
  onRemove: (key: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <ul className="mt-2 flex flex-wrap gap-2">
      {items.map((x) => (
        <li
          key={x.key}
          className="relative size-20 overflow-hidden rounded-2xl"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={x.preview} alt="" className="size-full object-cover" />
          {x.state === "uploading" && (
            <span className="absolute inset-0 grid place-items-center bg-black/40">
              <Loader2
                aria-label="Uploading"
                className="size-5 animate-spin text-white"
              />
            </span>
          )}
          {x.state === "error" && (
            <span className="absolute inset-0 grid place-items-center bg-black/60 text-xs text-white">
              Failed
            </span>
          )}
          <button
            type="button"
            aria-label="Remove photo"
            onClick={() => onRemove(x.key)}
            className="absolute right-1 top-1 grid size-6 place-items-center rounded-full bg-black/60 text-white"
          >
            <X className="size-3.5" aria-hidden />
          </button>
        </li>
      ))}
    </ul>
  );
}
