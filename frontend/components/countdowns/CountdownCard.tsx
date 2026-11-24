"use client";
/**
 * @file components/countdowns/CountdownCard.tsx
 * @brief Countdown card: big day number, title, date, follow toggle.
 */
import Link from "next/link";
import { Card } from "@/components/ui";
import { mediaThumbUrl } from "@/lib/api/media";
import { daysUntil, type Countdown } from "@/lib/api/countdowns";
import { FollowButton } from "./FollowButton";

/**
 * @brief Render a countdown (days computed in the viewer's timezone).
 * @param c countdown
 * @param now optional clock override (tests)
 * @return card
 */
export function CountdownCard({ c, now }: { c: Countdown; now?: Date }) {
  const days = daysUntil(c.next_date, now);
  const today = days === 0;
  const date = new Date(`${c.next_date}T00:00:00`).toLocaleDateString(
    undefined,
    { dateStyle: "long" },
  );
  return (
    <Card
      data-testid="countdown-card"
      className={`flex flex-col gap-3 p-4 ${today ? "ring-accent ring-2" : ""}`}
      style={
        c.cover_media_id
          ? {
              backgroundImage: `linear-gradient(rgb(0 0 0 / .65), rgb(0 0 0 / .65)), url(${mediaThumbUrl(c.cover_media_id)})`,
              backgroundSize: "cover",
              color: "#fff",
            }
          : undefined
      }
    >
      <div className="flex items-center gap-3">
        {c.emoji ? (
          <span aria-hidden className="text-3xl">
            {c.emoji}
          </span>
        ) : null}
        <Link
          href={`/app/countdowns/${c.id}`}
          className="text-lg font-semibold hover:underline"
        >
          {c.title}
        </Link>
      </div>
      <div
        className={
          today
            ? "text-4xl font-bold motion-safe:animate-pulse"
            : "text-4xl font-bold"
        }
      >
        {today ? (
          "Today!"
        ) : days > 0 ? (
          <>
            {days}{" "}
            <span className="text-base font-medium">
              {days === 1 ? "day" : "days"} until
            </span>
          </>
        ) : (
          <span className="text-base font-medium">
            {-days} {days === -1 ? "day" : "days"} ago
          </span>
        )}
      </div>
      <p className="text-sm opacity-80">
        {date}
        {c.repeat_yearly ? " · repeats yearly" : ""}
      </p>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm">
          {c.follower_count} {c.follower_count === 1 ? "follower" : "followers"}
        </span>
        <FollowButton id={c.id} following={c.following} />
      </div>
    </Card>
  );
}
