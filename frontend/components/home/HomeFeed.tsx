"use client";
/**
 * @file components/home/HomeFeed.tsx
 * @brief Unified live feed: composer, posts + activity lines, new-items pill,
 *        infinite scroll.
 */
import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AlertCircle, MessageSquarePlus, Trophy } from "lucide-react";
import { Button, Card, EmptyState, Skeleton } from "@/components/ui";
import { PostComposer } from "@/components/feed/PostComposer";
import { KudosComposer } from "@/components/feed/KudosComposer";
import { PostCard } from "@/components/feed/PostCard";
import { ActivityLine } from "@/components/feed/ActivityLine";
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
  const reduced = useReducedMotion();
  const [kudosOpen, setKudosOpen] = React.useState(false);
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
        <PostComposer />
      </div>
      <div className="flex justify-end">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setKudosOpen(true)}
        >
          <Trophy className="size-4" aria-hidden="true" />
          Send Kudos
        </Button>
      </div>
      {kudosOpen ? (
        <KudosComposer open onClose={() => setKudosOpen(false)} />
      ) : null}
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
            <AnimatePresence>
              {items.map((i) => {
                const key = `${i.kind}:${i.id}`;
                const fresh = freshIds.has(key);
                return (
                  <motion.li
                    key={key}
                    data-testid="feed-item"
                    data-new={fresh ? "true" : undefined}
                    className="rounded-lg data-[new=true]:motion-safe:ring-2 data-[new=true]:motion-safe:ring-accent"
                    {...(reduced
                      ? {}
                      : {
                          layout: "position" as const,
                          initial: fresh ? { opacity: 0, y: -8 } : false,
                          animate: { opacity: 1, y: 0 },
                          exit: { opacity: 0, transition: { duration: 0.12 } },
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
  );
}

export default HomeFeed;
