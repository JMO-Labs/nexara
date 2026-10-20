"use client";
/**
 * @file components/home/HomeFeed.tsx
 * @brief Unified live feed: composer, posts + activity lines, new-items pill,
 *        infinite scroll.
 */
import * as React from "react";
import { Button, EmptyState } from "@/components/ui";
import { PostComposer } from "@/components/feed/PostComposer";
import { PostCard } from "@/components/feed/PostCard";
import { ActivityLine } from "@/components/feed/ActivityLine";
import { useHomeFeed } from "@/hooks/useHomeFeed";
import { NewItemsPill } from "./NewItemsPill";

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
  } = useHomeFeed();
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
      {!isLoading && isEmpty ? (
        <EmptyState
          title="Nothing here yet"
          action={<Button onClick={focusComposer}>Write the first post</Button>}
        />
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((i) => (
            <li
              key={`${i.kind}:${i.id}`}
              data-new={freshIds.has(`${i.kind}:${i.id}`) ? "true" : undefined}
              className="rounded-[1.25rem] data-[new=true]:motion-safe:ring-2 data-[new=true]:motion-safe:ring-accent"
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
      <div ref={sentinelRef} aria-hidden="true" className="h-1" />
    </div>
  );
}

export default HomeFeed;
