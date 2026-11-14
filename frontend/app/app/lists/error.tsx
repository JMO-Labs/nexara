"use client";
/**
 * @file app/app/lists/error.tsx
 * @brief Error boundary for every /app/lists route.
 */
import { ErrorCard } from "@/components/lists/pages/PageChrome";

/**
 * @brief Route error card with retry.
 * @param props error and reset from Next.js
 * @return error card
 */
export default function ListsError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <ErrorCard
      message="This page failed to load. Please try again."
      onRetry={reset}
    />
  );
}
