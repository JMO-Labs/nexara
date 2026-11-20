"use client";
/**
 * @file components/home/HomeFeed.tsx
 * @brief Unified live feed: composer, posts + activity lines, new-items pill,
 *        infinite scroll.
 */
import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useTranslations } from "next-intl";
import { AlertCircle, MessageSquarePlus, Trophy } from "lucide-react";
import { Button, Card, EmptyState, Skeleton } from "@/components/ui";
import { PostComposer } from "@/components/feed/PostComposer";
import { KudosComposer } from "@/components/feed/KudosComposer";
import { PostCard } from "@/components/feed/PostCard";
import { ActivityLine } from "@/components/feed/ActivityLine";
import { PromptPostCard } from "@/components/feed/PromptPostCard";
import { useActivePrompts } from "@/hooks/useActivePrompts";
import { useHomeFeed } from "@/hooks/useHomeFeed";
import type { FeedItem } from "@/lib/api/home";
import { cn } from "@/lib/utils";
import { NewItemsPill } from "./NewItemsPill";

const MotionCard = motion.create(Card);

export interface HomeFeedProps {
  /** Keep only items for which this returns true. */
  filter?: (item: FeedItem) => boolean;
  /** Scroll inside the parent tile (md+) instead of the window. */
  embedded?: boolean;
  /** Title for the empty state shown instead of "No posts yet". */
  emptyTitle?: string;
}

/**
 * @brief Home feed column.
 * @param filter optional item filter
 * @param embedded scroll within the tile at md+
 * @param emptyTitle custom empty-state title (e.g. scoped to a group)
 * @return feed element
 */
export function HomeFeed({
  filter,
  embedded = false,
  emptyTitle,
}: HomeFeedProps = {}) {
  const scrollRef = React.useRef<HTMLDivElement>(null);
  // Embedded feed scrolls inside the tile at md+; on phone the window scrolls.
  const tileScrollTop = React.useCallback(() => {
    const box = scrollRef.current;
    return box && box.scrollHeight > box.clientHeight
      ? box.scrollTop
      : window.scrollY;
  }, []);
  const {
    items: allItems,
    pending: allPending,
    reveal,
    freshIds,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isError,
    refetch,
  } = useHomeFeed({ getScrollTop: embedded ? tileScrollTop : undefined });
  const { data: prompts } = useActivePrompts();
  const [replyTo, setReplyTo] = React.useState<{
    id: string;
    title: string;
  } | null>(null);
  const reduced = useReducedMotion();
  const tk = useTranslations("kudos");
  const [kudosOpen, setKudosOpen] = React.useState(false);
  const composerRef = React.useRef<HTMLDivElement>(null);
  const sentinelRef = React.useRef<HTMLDivElement>(null);
  const nextRef = React.useRef({ fetchNextPage, hasNextPage });
  React.useEffect(() => {
    nextRef.current = { fetchNextPage, hasNextPage };
  });
  const items = React.useMemo(
    () => (filter ? allItems.filter(filter) : allItems),
    [allItems, filter],
  );
  const pending = React.useMemo(
    () => (filter ? allPending.filter(filter) : allPending),
    [allPending, filter],
  );
  const isEmpty = items.length === 0;

  React.useEffect(() => {
    const el = sentinelRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    // The container only scrolls at md+; below that the window scrolls.
    const inTile =
      embedded &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(min-width: 768px)").matches;
    const io = new IntersectionObserver(
      (entries) => {
        if (
          entries.some((e) => e.isIntersecting) &&
          nextRef.current.hasNextPage
        )
          nextRef.current.fetchNextPage();
      },
      inTile ? { root: scrollRef.current } : undefined,
    );
    io.observe(el);
    return () => io.disconnect();
  }, [isEmpty, embedded]);

  const onPill = () => {
    const opts: ScrollToOptions = {
      top: 0,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    };
    const box = scrollRef.current;
    if (embedded && box && box.scrollHeight > box.clientHeight)
      box.scrollTo?.(opts);
    else window.scrollTo(opts);
    reveal();
  };
  const focusComposer = () =>
    composerRef.current
      ?.querySelector<HTMLElement>('[contenteditable="true"], textarea')
      ?.focus();

  return (
    <div
      className={cn(
        "flex flex-col gap-4",
        embedded && "min-h-0 flex-1 md:relative",
      )}
    >
      <NewItemsPill count={pending.length} onClick={onPill} inline={embedded} />
      <div
        ref={scrollRef}
        data-feed-scroll={embedded ? "" : undefined}
        className={cn(
          "flex flex-col gap-4",
          embedded &&
            "md:min-h-0 md:flex-1 md:overflow-y-auto md:pr-1 md:[mask-image:linear-gradient(#000_92%,transparent)]",
        )}
      >
        <div ref={composerRef}>
          <PostComposer
            replyToPromptId={replyTo?.id}
            replyToPromptTitle={replyTo?.title}
            onClearReplyPrompt={() => setReplyTo(null)}
            onPosted={() => setReplyTo(null)}
          />
        </div>
        <div className="flex justify-end">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setKudosOpen(true)}
          >
            <Trophy className="size-4" aria-hidden="true" />
            {tk("sendButton")}
          </Button>
        </div>
        {kudosOpen ? (
          <KudosComposer open onClose={() => setKudosOpen(false)} />
        ) : null}
        {prompts && prompts.length > 0 && (
          <section aria-label="Active prompts" className="flex flex-col gap-2">
            {prompts.map((p) => (
              <PromptPostCard
                key={p.id}
                post={p}
                onReply={(id, title) => {
                  setReplyTo({ id, title });
                  focusComposer();
                }}
              />
            ))}
          </section>
        )}
        <AnimatePresence mode="wait" initial={false}>
          {isLoading ? (
            <motion.div
              key="loading"
              exit={{ opacity: 0 }}
              role="status"
              aria-label="Loading feed"
              className="flex flex-col gap-2"
            >
              {[0, 1, 2].map((n) => (
                <MotionCard
                  key={n}
                  data-testid="feed-skeleton"
                  data-delay={String(n * 0.08)}
                  aria-hidden="true"
                  initial={reduced ? false : { opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: n * 0.08, duration: 0.2 }}
                  className="flex flex-col gap-2 p-3 md:p-4"
                >
                  <Skeleton width="40%" height={16} role="presentation" />
                  <Skeleton height={64} rounded="md" role="presentation" />
                </MotionCard>
              ))}
            </motion.div>
          ) : isError && isEmpty ? (
            <EmptyState
              key="error"
              icon={AlertCircle}
              title="Failed to load feed"
              description="Something went wrong. Check your connection and try again."
              action={<Button onClick={() => refetch()}>Retry</Button>}
            />
          ) : isEmpty ? (
            <EmptyState
              key="empty"
              icon={MessageSquarePlus}
              title={emptyTitle ?? "No posts yet"}
              description={
                emptyTitle
                  ? undefined
                  : "Share an update with your community to get things started."
              }
              action={
                <Button onClick={focusComposer}>Create your first post</Button>
              }
            />
          ) : (
            <ul key="list" className="flex flex-col gap-2">
              <AnimatePresence>
                {items.map((i) => {
                  const key = `${i.kind}:${i.id}`;
                  const fresh = freshIds.has(key);
                  return (
                    <motion.li
                      key={key}
                      data-testid="feed-item"
                      data-new={fresh ? "true" : undefined}
                      className={cn(
                        "rounded-lg data-[new=true]:motion-safe:ring-2 data-[new=true]:motion-safe:ring-accent",
                        embedded && "glass-item",
                      )}
                      {...(reduced
                        ? {}
                        : {
                            layout: "position" as const,
                            initial: fresh ? { opacity: 0, y: -8 } : false,
                            animate: { opacity: 1, y: 0 },
                            exit: {
                              opacity: 0,
                              transition: { duration: 0.12 },
                            },
                            transition: { duration: 0.2, ease: "easeOut" },
                          })}
                    >
                      {i.kind === "post" ? (
                        <PostCard post={i.post} />
                      ) : (
                        <ActivityLine item={i.activity} />
                      )}
                    </motion.li>
                  );
                })}
              </AnimatePresence>
            </ul>
          )}
        </AnimatePresence>
        <div ref={sentinelRef} aria-hidden="true" className="h-1" />
      </div>
    </div>
  );
}

export default HomeFeed;
