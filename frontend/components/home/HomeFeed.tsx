"use client";
/**
 * @file components/home/HomeFeed.tsx
 * @brief Unified live feed: composer, posts + activity lines, new-items pill,
 *        infinite scroll.
 */
import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AlertCircle, MessageSquarePlus } from "lucide-react";
import { Button, Card, EmptyState, Skeleton } from "@/components/ui";
import { PostComposer } from "@/components/feed/PostComposer";
import { PostCard } from "@/components/feed/PostCard";
import { ActivityLine } from "@/components/feed/ActivityLine";
import { PromptPostCard } from "@/components/feed/PromptPostCard";
import { useActivePrompts } from "@/hooks/useActivePrompts";
import { useHomeFeed } from "@/hooks/useHomeFeed";
import { NewItemsPill } from "./NewItemsPill";

const MotionCard = motion.create(Card);

/**
 * @brief Home feed column.
 * @return feed element
 */
export function HomeFeed() {
  const {
    items,
    pending,
    reveal,
    freshIds,
    fetchNextPage,
    hasNextPage,
    isLoading,
    isError,
    refetch,
  } = useHomeFeed();
  const { data: prompts } = useActivePrompts();
  const [replyTo, setReplyTo] = React.useState<{
    id: string;
    title: string;
  } | null>(null);
  const reduced = useReducedMotion();
  const composerRef = React.useRef<HTMLDivElement>(null);
  const sentinelRef = React.useRef<HTMLDivElement>(null);
  const nextRef = React.useRef({ fetchNextPage, hasNextPage });
  React.useEffect(() => {
    nextRef.current = { fetchNextPage, hasNextPage };
  });
  const isEmpty = items.length === 0;

  React.useEffect(() => {
    const el = sentinelRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting) && nextRef.current.hasNextPage)
        nextRef.current.fetchNextPage();
    });
    io.observe(el);
    return () => io.disconnect();
  }, [isEmpty]);

  const onPill = () => {
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
    reveal();
  };
  const focusComposer = () =>
    composerRef.current
      ?.querySelector<HTMLElement>('[contenteditable="true"], textarea')
      ?.focus();

  return (
    <div className="flex flex-col gap-4">
      <NewItemsPill count={pending.length} onClick={onPill} />
      <div ref={composerRef}>
        <PostComposer
          replyToPromptId={replyTo?.id}
          replyToPromptTitle={replyTo?.title}
          onClearReplyPrompt={() => setReplyTo(null)}
          onPosted={() => setReplyTo(null)}
        />
      </div>
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
            title="No posts yet"
            description="Share an update with your community to get things started."
            action={
              <Button onClick={focusComposer}>Create your first post</Button>
            }
          />
        ) : (
          <ul key="list" className="flex flex-col gap-2">
            {items.map((i) => (
              <li
                key={`${i.kind}:${i.id}`}
                data-new={
                  freshIds.has(`${i.kind}:${i.id}`) ? "true" : undefined
                }
                className="rounded-lg data-[new=true]:motion-safe:ring-2 data-[new=true]:motion-safe:ring-accent"
              >
                {i.kind === "post" ? (
                  <PostCard post={i.post} />
                ) : (
                  <ActivityLine item={i.activity} />
                )}
              </li>
            ))}
          </ul>
        )}
      </AnimatePresence>
      <div ref={sentinelRef} aria-hidden="true" className="h-1" />
    </div>
  );
}

export default HomeFeed;
