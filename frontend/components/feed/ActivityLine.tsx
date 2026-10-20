/**
 * @file components/feed/ActivityLine.tsx
 * @brief One-line activity entry for the home feed (avatar, sentence, time).
 */
import * as React from "react";
import Link from "next/link";
import { formatDistanceToNowStrict } from "date-fns";
import { Avatar } from "@/components/ui";
import type { ActivityItem } from "@/lib/api/home";

/**
 * @brief Build the sentence for an activity item.
 * @param i activity item
 * @return plain-text sentence
 */
function sentence(i: ActivityItem): string {
  const who = i.actor_name;
  const obj = i.object_title ?? "a post";
  const multi = i.count > 1 ? ` (${i.count})` : "";
  switch (i.verb) {
    case "post.commented":
      return `${who} commented on ${obj}${multi}`;
    case "post.reacted":
      return `${who} reacted to ${obj}${multi}`;
    case "event.rsvp":
      return `${who} is going to ${i.object_title ?? "an event"}${multi}`;
    case "subgroup.joined":
    case "member.joined":
      return `${who} joined ${i.container_title ?? "a group"}${multi}`;
    case "media.uploaded":
      return i.count > 1
        ? `${who} added ${i.count} photos`
        : `${who} added a photo`;
    default:
      return `${who} was active${multi}`;
  }
}

/**
 * @brief Route for the item's object, if one exists.
 * @param i activity item
 * @return same-origin path or null
 */
function hrefFor(i: ActivityItem): string | null {
  if (i.object_type === "post")
    return `/app/post/${encodeURIComponent(i.object_id)}`;
  if (i.object_type === "event")
    return `/app/events?event=${encodeURIComponent(i.object_id)}`;
  return null;
}

/**
 * @brief Compact activity row.
 * @param item activity item from the feed
 * @return row element, linked when the object has a route
 */
export function ActivityLine({ item }: { item: ActivityItem }) {
  const href = hrefFor(item);
  let ago = "";
  try {
    ago = formatDistanceToNowStrict(new Date(item.created_at), {
      addSuffix: true,
    });
  } catch {
    /* invalid date: show nothing */
  }
  const body = (
    <>
      <Avatar name={item.actor_name} size="sm" />
      <span className="min-w-0 flex-1 truncate">{sentence(item)}</span>
      <time dateTime={item.created_at} className="shrink-0 text-xs opacity-70">
        {ago}
      </time>
    </>
  );
  const cls = "flex items-center gap-2 px-1 py-1 text-sm text-ink";
  return href ? (
    <Link
      href={href}
      className={`${cls} rounded-lg hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent`}
    >
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export default ActivityLine;
