"use client";
/**
 * @file components/home/WelcomeBanner.tsx
 * @brief Welcome banner for the home page hub.
 *        Displays time-aware greeting, user name, and three stat chips
 *        (new posts, upcoming events, unread notifications).
 *        Shows skeleton loaders while data is loading.
 * @param userName             Authenticated user's display name.
 * @param newPosts             Count of new posts since last visit.
 * @param upcomingEvents       Count of events in next 7 days.
 * @param unreadNotifications  Unread notification count.
 * @param isLoading            Shows skeleton UI when true.
 */
import * as React from "react";
import Link from "next/link";
import { Skeleton } from "@/components/ui/Skeleton";

export interface WelcomeBannerProps {
  userName: string;
  newPosts: number;
  upcomingEvents: number;
  unreadNotifications: number;
  isLoading?: boolean;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

interface StatChipProps {
  count: number;
  label: string;
  href: string;
  ariaLabel: string;
}

function StatChip({ count, label, href, ariaLabel }: StatChipProps) {
  return (
    <Link
      href={href}
      aria-label={ariaLabel}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/20 hover:bg-white/30 text-white text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
    >
      <span className="font-bold">{count}</span>
      <span>{label}</span>
    </Link>
  );
}

export function WelcomeBanner({
  userName,
  newPosts,
  upcomingEvents,
  unreadNotifications,
  isLoading = false,
}: WelcomeBannerProps) {
  const greeting = getGreeting();

  if (isLoading) {
    return (
      <div className="rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-6 flex flex-col gap-4">
        <Skeleton width={220} height={32} rounded="md" />
        <div className="flex flex-wrap gap-2">
          <Skeleton width={120} height={32} rounded="pill" />
          <Skeleton width={140} height={32} rounded="pill" />
          <Skeleton width={160} height={32} rounded="pill" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-6 flex flex-col gap-4">
      {/* Greeting — sufficient contrast: white text on dark gradient (>4.5:1) */}
      <h1 className="text-2xl font-bold text-white">
        {greeting}, {userName}
      </h1>

      <div
        className="flex flex-wrap gap-2"
        role="list"
        aria-label="Activity summary"
      >
        <div role="listitem">
          <StatChip
            count={newPosts}
            label="new posts"
            href="/app#feed"
            ariaLabel={`${newPosts} new posts since your last visit`}
          />
        </div>
        <div role="listitem">
          <StatChip
            count={upcomingEvents}
            label="upcoming events"
            href="/app/events"
            ariaLabel={`${upcomingEvents} upcoming events in the next 7 days`}
          />
        </div>
        <div role="listitem">
          <StatChip
            count={unreadNotifications}
            label="notifications"
            href="/app#activity"
            ariaLabel={`${unreadNotifications} unread notifications`}
          />
        </div>
      </div>
    </div>
  );
}

export default WelcomeBanner;
