"use client";
/**
 * @file components/stories/StoryRequests.tsx
 * @brief Open story requests for me: answer by voice (records, posts, links)
 *        or pass quietly (the asker is never told).
 */
import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card } from "@/components/ui";
import { Recorder } from "@/components/audio/Recorder";
import { createPost, type CreatePostBody } from "@/lib/api/posts";
import {
  answerStory,
  declineStory,
  listStoryRequests,
  type StoryRequest,
} from "@/lib/api/stories";
import { useToasts } from "@/stores/toasts";

export const REQUESTS_KEY = ["story-requests"] as const;

function RequestRow({ req }: { req: StoryRequest }) {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const [recording, setRecording] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const done = () => {
    qc.invalidateQueries({ queryKey: REQUESTS_KEY });
    qc.invalidateQueries({ queryKey: ["stories"] });
  };
  return (
    <li className="flex flex-col gap-2">
      <p className="text-sm text-muted">{req.asker.display_name} asks</p>
      <p className="text-base font-medium">{req.question}</p>
      {recording ? (
        <Recorder
          onCancel={() => setRecording(false)}
          onReady={async (m) => {
            try {
              const body: CreatePostBody & { visibility?: string } = {
                content: "",
                media_ids: [m.id],
                visibility: "community",
              };
              const post = await createPost(body);
              await answerStory(req.id, post.id);
              push({ variant: "success", message: "Story shared" });
              done();
            } catch {
              setError("Couldn't share your story. Try again.");
            }
          }}
        />
      ) : (
        <div className="flex gap-2">
          <Button className="min-h-11" onClick={() => setRecording(true)}>
            Answer by voice
          </Button>
          <Button
            variant="ghost"
            className="min-h-11"
            onClick={() => declineStory(req.id).then(done)}
          >
            Not now
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </li>
  );
}

/**
 * @return card of open requests, or null when there are none
 */
export function StoryRequests() {
  const q = useQuery({ queryKey: REQUESTS_KEY, queryFn: listStoryRequests });
  const items = q.data?.incoming ?? [];
  if (items.length === 0) return null;
  return (
    <Card
      role="region"
      aria-label="Story requests"
      className="flex flex-col gap-4 p-4"
    >
      <h3 className="text-lg font-semibold">
        People would love to hear from you
      </h3>
      <ul className="flex flex-col gap-4">
        {items.map((r) => (
          <RequestRow key={r.id} req={r} />
        ))}
      </ul>
    </Card>
  );
}

export default StoryRequests;
