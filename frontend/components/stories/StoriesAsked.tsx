"use client";
/**
 * @file components/stories/StoriesAsked.tsx
 * @brief "Stories you asked for": my outgoing requests. The API already maps
 *        a decline to "open", so it reads "Waiting" until expiry.
 */
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui";
import { REQUESTS_KEY } from "@/components/stories/StoryRequests";
import { listStoryRequests, type StoryRequest } from "@/lib/api/stories";

/**
 * @param iso ISO timestamp
 * @param now reference time (tests)
 * @return e.g. "3 days ago"
 */
export function relativeDate(iso: string, now = Date.now()): string {
  const days = Math.round((new Date(iso).getTime() - now) / 86_400_000);
  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
    days,
    "day",
  );
}

function Row({ r }: { r: StoryRequest }) {
  return (
    <li className="flex flex-col gap-1">
      <p className="text-sm text-muted">
        {r.teller.display_name} · {relativeDate(r.created_at)}
      </p>
      <p className="text-base font-medium">{r.question}</p>
      {r.status === "answered" && r.post_id ? (
        <Link
          href={`/app/post/${r.post_id}`}
          className="min-h-11 self-start text-sm text-accent underline underline-offset-2"
        >
          Listen to their story
        </Link>
      ) : (
        <p className="text-sm text-muted">
          {r.status === "expired" ? "Expired" : "Waiting"}
        </p>
      )}
    </li>
  );
}

/**
 * @return card listing my asks, with an empty state pointing at the directory
 */
export function StoriesAsked() {
  const q = useQuery({ queryKey: REQUESTS_KEY, queryFn: listStoryRequests });
  if (!q.data) return null;
  const items = q.data.outgoing;
  return (
    <Card
      role="region"
      aria-label="Stories you asked for"
      className="flex flex-col gap-4 p-4"
    >
      <h3 className="text-lg font-semibold">Stories you asked for</h3>
      {items.length === 0 ? (
        <div className="flex flex-col items-start gap-2">
          <p className="text-sm text-muted">
            You haven&apos;t asked anyone for a story yet.
          </p>
          <Link
            href="/app/members"
            className="inline-flex min-h-11 items-center rounded-full bg-surface-strong px-4 text-sm font-semibold text-bg outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Ask for a story
          </Link>
        </div>
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((r) => (
            <Row key={r.id} r={r} />
          ))}
        </ul>
      )}
    </Card>
  );
}

export default StoriesAsked;
