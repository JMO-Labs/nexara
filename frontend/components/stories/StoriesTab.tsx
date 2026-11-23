"use client";
/**
 * @file components/stories/StoriesTab.tsx
 * @brief Profile "Stories" tab: open requests (own profile) or an ask button
 *        (others), then voice/answer posts newest first with the question
 *        shown above the player.
 */
import * as React from "react";
import Link from "next/link";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Mic } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { AskStoryDialog } from "@/components/stories/AskStoryDialog";
import { StoriesAsked } from "@/components/stories/StoriesAsked";
import { StoryRequests } from "@/components/stories/StoryRequests";
import { userStories, type StoryItem } from "@/lib/api/stories";

function Story({ item }: { item: StoryItem }) {
  const audio = item.post.media.filter((m) => m.mime_type.startsWith("audio/"));
  return (
    <li className="glass-item flex flex-col gap-2 rounded-[22px] p-4">
      {item.question && (
        <p className="text-base font-medium">{item.question}</p>
      )}
      {audio.map((m) => (
        <AudioPlayer key={m.id} src={m.url} label="Story recording" />
      ))}
      {item.post.content && <p className="text-sm">{item.post.content}</p>}
      <Link
        href={`/app/post/${item.post.id}`}
        className="self-start text-sm text-accent underline underline-offset-2"
      >
        {new Date(item.post.created_at).toLocaleDateString()}
      </Link>
    </li>
  );
}

/**
 * @param userId profile owner
 * @param name first name
 * @param isSelf viewer owns this profile
 * @return tab body
 */
export function StoriesTab({
  userId,
  name,
  isSelf,
}: {
  userId: string;
  name: string;
  isSelf: boolean;
}) {
  const q = useInfiniteQuery({
    queryKey: ["stories", userId],
    queryFn: ({ pageParam }) => userStories(userId, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_cursor,
  });
  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <div className="flex flex-col gap-4">
      {isSelf ? (
        <>
          <StoryRequests />
          <StoriesAsked />
        </>
      ) : (
        <div>
          <AskStoryDialog userId={userId} name={name} />
        </div>
      )}
      {q.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Mic}
          title="No stories yet"
          description={
            isSelf
              ? "Record a voice note from the composer to start your collection."
              : `${name} hasn't shared any stories you can see.`
          }
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((i) => (
            <Story key={i.post.id} item={i} />
          ))}
        </ul>
      )}
      {q.hasNextPage && (
        <Button
          variant="ghost"
          className="min-h-11 self-center"
          onClick={() => q.fetchNextPage()}
          disabled={q.isFetchingNextPage}
        >
          Load more
        </Button>
      )}
    </div>
  );
}

export default StoriesTab;
