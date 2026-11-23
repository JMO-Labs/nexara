"use client";
/**
 * @file components/newsletter/NewsletterAdminBar.tsx
 * @brief Admin-only pin / hide controls for the newsletter's posts. Not printed.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui";
import {
  setNewsletterOverride,
  type NewsPost,
  type OverrideAction,
} from "@/lib/api/newsletter";

/**
 * @param props month, shown posts and hidden posts
 * @return a "Curate" panel hidden from print
 */
export function NewsletterAdminBar({
  month,
  posts,
  hidden,
}: {
  month: string;
  posts: NewsPost[];
  hidden: NewsPost[];
}) {
  const qc = useQueryClient();
  const set = useMutation({
    mutationFn: (v: { id: string; action: OverrideAction }) =>
      setNewsletterOverride(month, v.id, v.action),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["newsletter", month] }),
  });
  const row = (p: NewsPost, buttons: React.ReactNode) => (
    <li key={p.id} className="flex items-center justify-between gap-3 py-2">
      <span className="min-w-0 truncate text-sm text-ink">
        {p.author_name}: {p.excerpt}
      </span>
      <span className="flex shrink-0 gap-2">{buttons}</span>
    </li>
  );
  const act = (p: NewsPost, label: string, action: OverrideAction) => (
    <Button
      key={label}
      size="sm"
      variant="secondary"
      disabled={set.isPending}
      aria-label={`${label} post by ${p.author_name}`}
      onClick={() => set.mutate({ id: p.id, action })}
    >
      {label}
    </Button>
  );
  return (
    <section
      aria-label="Curate this newsletter"
      className="glass mb-6 rounded-2xl p-4 print:hidden"
    >
      <h2 className="text-base font-medium text-ink">Curate</h2>
      <p className="text-sm text-muted">
        Pin a post to the top or hide it. Members still only see posts they can
        open.
      </p>
      <ul className="m-0 list-none divide-y divide-[var(--nx-glass-edge)] p-0">
        {posts.map((p) =>
          row(
            p,
            <>
              {act(p, p.pinned ? "Unpin" : "Pin", p.pinned ? null : "pin")}
              {act(p, "Hide", "hide")}
            </>,
          ),
        )}
        {hidden.map((p) => row(p, act(p, "Restore", null)))}
      </ul>
    </section>
  );
}
