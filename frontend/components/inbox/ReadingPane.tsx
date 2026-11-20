"use client";
/**
 * @file components/inbox/ReadingPane.tsx
 * @brief Inbox reading pane: full notification (actions + open link), saved
 *        post, or list detail. Empty state when nothing is selected.
 */
import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, ChevronLeft, MailOpen } from "lucide-react";
import { Button } from "@/components/ui";
import { IconButton } from "@/components/ui/IconButton";
import { PostCard } from "@/components/feed/PostCard";
import { ListDetailPanel } from "@/components/lists/ListDetailPanel";
import { WithList } from "@/components/lists/pages/ListDetailView";
import { callAction } from "@/lib/api/notifications";
import { safeInternalLink } from "@/lib/safeLink";
import { renderNotif } from "@/lib/notifications/renderers";
import { useTranslations } from "next-intl";
import type { InboxEntry } from "./useInboxItems";

/**
 * @brief Reading pane for the selected entry.
 * @param entry selected entry or null
 * @param onBack phone/tablet back to the list
 * @return pane content
 */
export function ReadingPane({
  entry,
  onBack,
}: {
  entry: InboxEntry | null;
  onBack: () => void;
}) {
  if (!entry)
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <span className="glass-item grid size-14 place-items-center rounded-full">
          <MailOpen className="size-6 text-muted" aria-hidden="true" />
        </span>
        <p className="text-sm text-muted">Select an item to read it here.</p>
      </div>
    );
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 px-5 pt-4 lg:hidden">
        <IconButton
          aria-label="Back to list"
          variant="ghost"
          size="sm"
          onClick={onBack}
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
        </IconButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-6 pt-4 md:px-8">
        {entry.kind === "notif" && <NotifDetail entry={entry} />}
        {entry.kind === "saved" && <PostCard post={entry.post} />}
        {entry.kind === "list" && (
          <WithList id={entry.list.id}>
            {(list, communityId) => (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-2xl font-medium tracking-tight">
                    {list.title}
                  </h2>
                  <Button asChild variant="secondary" size="sm">
                    <Link href={`/app/lists/${list.id}`}>
                      Open list{" "}
                      <ArrowUpRight className="size-4" aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
                <ListDetailPanel list={list} communityId={communityId} />
              </div>
            )}
          </WithList>
        )}
      </div>
    </div>
  );
}

function NotifDetail({
  entry,
}: {
  entry: Extract<InboxEntry, { kind: "notif" }>;
}) {
  const t = useTranslations();
  const qc = useQueryClient();
  const [pending, setPending] = useState<string | null>(null);
  const r = renderNotif(entry.type, entry.notif.payload ?? {}, (k) => t(k));
  const link = safeInternalLink(entry.link);
  const Icon = entry.Icon;
  const act = async (key: string) => {
    setPending(key);
    try {
      await callAction(entry.notif.id, key);
      void qc.invalidateQueries({ queryKey: ["notifications"] });
    } finally {
      setPending(null);
    }
  };
  return (
    <article className="flex max-w-[72ch] flex-col gap-4">
      <header className="flex items-start gap-4">
        {Icon && (
          <span className="glass-item grid size-12 shrink-0 place-items-center rounded-full">
            <Icon className="size-5" aria-hidden="true" />
          </span>
        )}
        <div className="min-w-0">
          <h2 className="text-2xl font-medium tracking-tight">{entry.title}</h2>
          <p className="text-sm text-muted">
            {format(new Date(entry.time), "EEEE, MMMM d 'at' p")}
          </p>
        </div>
      </header>
      {entry.snippet && (
        <p className="text-[15px] leading-relaxed">{entry.snippet}</p>
      )}
      {(r.actions.length > 0 || link) && (
        <div className="flex flex-wrap gap-2">
          {r.actions.map((a) => (
            <Button
              key={a.key}
              size="sm"
              variant={
                a.style === "danger"
                  ? "destructive"
                  : a.style === "neutral"
                    ? "secondary"
                    : "primary"
              }
              loading={pending === a.key}
              onClick={() => void act(a.key)}
            >
              {a.label}
            </Button>
          ))}
          {link && (
            <Button asChild size="sm" variant="secondary">
              <Link href={link}>
                Open <ArrowUpRight className="size-4" aria-hidden="true" />
              </Link>
            </Button>
          )}
        </div>
      )}
    </article>
  );
}
