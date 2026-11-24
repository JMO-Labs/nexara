"use client";
/**
 * @file components/members/MemberTaggedTab.tsx
 * @brief Profile "Tagged" tab: posts and photos this person is tagged in,
 *        limited by the server to what the viewer may see.
 */
import * as React from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { AtSign, Images } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { Segmented } from "@/components/ui/page";
import { PostCard } from "@/components/feed/PostCard";
import { PhotoGrid } from "@/components/galleries/PhotoGrid";
import { getTagged } from "@/lib/api/tags";

type Kind = "posts" | "photos";

/**
 * @brief Tagged tab.
 * @param userId profile owner
 * @param name first name for empty text
 * @return tab body
 */
export function MemberTaggedTab({
  userId,
  name,
}: {
  userId: string;
  name: string;
}) {
  const [kind, setKind] = React.useState<Kind>("posts");
  const q = useInfiniteQuery({
    queryKey: ["tagged", userId, kind],
    queryFn: ({ pageParam }) => getTagged(userId, kind, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_before,
  });
  const posts = q.data?.pages.flatMap((p) => p.posts) ?? [];
  const media = q.data?.pages.flatMap((p) => p.media_ids) ?? [];
  const nsfw = q.data?.pages.flatMap((p) => p.nsfw_media_ids ?? []);
  const empty = kind === "posts" ? !posts.length : !media.length;

  return (
    <div className="flex flex-col gap-4">
      <Segmented
        label="Tagged in"
        value={kind}
        onChange={setKind}
        options={[
          { value: "posts", label: "Posts" },
          { value: "photos", label: "Photos" },
        ]}
      />
      {q.isLoading ? (
        <Skeleton height={160} rounded="lg" />
      ) : empty ? (
        <EmptyState
          compact
          icon={kind === "posts" ? AtSign : Images}
          title={`${name} isn't tagged in any ${kind} you can see`}
        />
      ) : kind === "posts" ? (
        <div className="mx-auto flex w-full max-w-[760px] flex-col gap-4">
          {posts.map((p) => (
            <PostCard key={p.id} post={p} />
          ))}
        </div>
      ) : (
        <PhotoGrid mediaIds={media} nsfwIds={nsfw} />
      )}
      {q.hasNextPage && (
        <Button
          variant="ghost"
          size="sm"
          className="self-center"
          loading={q.isFetchingNextPage}
          onClick={() => void q.fetchNextPage()}
        >
          Load more
        </Button>
      )}
    </div>
  );
}
