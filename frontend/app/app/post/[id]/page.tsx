"use client";
/**
 * @file app/app/post/[id]/page.tsx
 * @brief Full-screen post detail (mobile + direct/refresh navigation).
 */
import { use } from "react";
import { AlertCircle } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { PageHeader, Panel } from "@/components/ui/page";
import { PostCard } from "@/components/feed/PostCard";
import { CommentThread } from "@/components/feed/CommentThread";
import { usePost } from "@/hooks/usePosts";

export default function PostPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: post, isLoading, isError, refetch } = usePost(id);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col">
      <PageHeader title="Post" back={{ href: "/app", label: "Back to feed" }} />
      {isLoading ? (
        <div
          role="status"
          aria-label="Loading post"
          className="flex flex-col gap-4"
        >
          <Skeleton height={240} rounded="lg" />
          <Skeleton height={48} />
          <Skeleton height={48} />
        </div>
      ) : isError ? (
        <EmptyState
          icon={AlertCircle}
          title="Couldn't load post"
          description="Check your connection and try again."
          action={
            <Button variant="secondary" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      ) : !post ? (
        <EmptyState
          title="Post not found"
          description="It may have been deleted."
        />
      ) : (
        <div className="flex flex-col gap-4">
          <PostCard post={post} />
          <Panel title="Comments">
            <CommentThread postId={post.id} />
          </Panel>
        </div>
      )}
    </div>
  );
}
