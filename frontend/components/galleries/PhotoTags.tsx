"use client";
/**
 * @file components/galleries/PhotoTags.tsx
 * @brief Lightbox tag bar: who is in this photo (links + remove) and a
 *        "Tag someone" picker. Server enforces who may tag/remove.
 */
import * as React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Tag as TagIcon, X } from "lucide-react";
import { MentionMenu } from "@/components/mentions/MentionMenu";
import { matchMembers, useMembersList } from "@/hooks/useMembersList";
import { listTags, removeTag, tagPhoto } from "@/lib/api/tags";
import { useSession } from "@/stores/session";

/**
 * @brief Tags for one photo.
 * @param mediaId photo id
 * @return tag bar
 */
export function PhotoTags({ mediaId }: { mediaId: string }) {
  const qc = useQueryClient();
  const me = useSession((s) => s.user);
  const key = ["tags", "media", mediaId];
  const tags = useQuery({
    queryKey: key,
    queryFn: () => listTags("media", mediaId),
    retry: false,
  });
  const { data: members = [] } = useMembersList();
  const [adding, setAdding] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [active, setActive] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const tagged = new Set((tags.data ?? []).map((t) => t.user.id));
  const items = adding
    ? matchMembers(members, q).filter((u) => !tagged.has(u.id))
    : [];
  const idx = Math.min(active, Math.max(items.length - 1, 0));

  const add = useMutation({
    mutationFn: (userId: string) => tagPhoto(mediaId, userId),
    onSuccess: (next) => {
      qc.setQueryData(key, next);
      setQ("");
      setError(null);
    },
    onError: (e) => setError(e instanceof Error ? e.message : "Couldn't tag."),
  });
  const remove = useMutation({
    mutationFn: removeTag,
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }),
    onError: (e) =>
      setError(e instanceof Error ? e.message : "Couldn't remove tag."),
  });

  if (tags.isError) return null; // not visible to this viewer

  return (
    <div
      className="flex flex-wrap items-center justify-center gap-2 px-4 pb-4"
      onClick={(e) => e.stopPropagation()}
    >
      {(tags.data ?? []).map((t) => (
        <span
          key={t.id}
          className="flex items-center gap-1 rounded-full bg-white/15 py-1 pr-1 pl-3 text-sm text-white"
        >
          <Link href={`/app/members/${t.user.id}`} className="hover:underline">
            {t.user.display_name}
          </Link>
          {(t.user.id === me?.id || t.tagged_by === me?.id) && (
            <button
              type="button"
              aria-label={`Remove tag ${t.user.display_name}`}
              onClick={() => remove.mutate(t.id)}
              className="grid size-6 place-items-center rounded-full hover:bg-white/20"
            >
              <X className="size-3.5" aria-hidden />
            </button>
          )}
        </span>
      ))}
      {adding ? (
        <span className="relative">
          <MentionMenu
            items={items}
            active={idx}
            onPick={(u) => add.mutate(u.id)}
            className="absolute bottom-full left-0 mb-2"
          />
          <input
            autoFocus
            aria-label="Tag someone"
            placeholder="Type a name"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActive(0);
            }}
            onBlur={() => !q && setAdding(false)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault();
                const d = e.key === "ArrowDown" ? 1 : -1;
                setActive((idx + d + items.length) % Math.max(items.length, 1));
              } else if (e.key === "Enter" && items[idx]) {
                e.preventDefault();
                add.mutate(items[idx].id);
              }
            }}
            className="w-44 rounded-full bg-white/15 px-3 py-1.5 text-sm text-white outline-none placeholder:text-white/60 focus-visible:outline-2 focus-visible:outline-white"
          />
        </span>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1.5 text-sm text-white hover:bg-white/25"
        >
          <TagIcon className="size-3.5" aria-hidden /> Tag someone
        </button>
      )}
      {error && (
        <p role="alert" className="w-full text-center text-xs text-red-200">
          {error}
        </p>
      )}
    </div>
  );
}
