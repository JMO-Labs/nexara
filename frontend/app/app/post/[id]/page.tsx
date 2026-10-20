"use client";
/**
 * @file app/app/post/[id]/page.tsx
 * @brief Full-screen post detail (mobile + direct/refresh navigation).
 */
import { use } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { PostCard } from "@/components/feed/PostCard";
import { CommentThread } from "@/components/feed/CommentThread";
import { usePost } from "@/hooks/usePosts";

export default function PostPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: post, isLoading, isError } = usePost(id);

  return (
    <div className="mx-auto flex w-full max-w-180 flex-col gap-4">
      <div>
        <Button asChild variant="ghost" size="sm" className="min-h-11">
          <Link href="/app">
            <ChevronLeft className="size-4" aria-hidden="true" />
            Back to feed
          </Link>
        </Button>
      </div>
      {isLoading ? (
        <Skeleton height={240} rounded="lg" />
      ) : isError || !post ? (
        <EmptyState
          title="Post not found"
          description="It may have been deleted."
        />
      ) : (
        <div className="flex flex-col gap-4">
          <PostCard post={post} />
          <CommentThread postId={post.id} />
        </div>
      )}
    </div>
  );
}
