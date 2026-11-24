"use client";
/**
 * @file hooks/useAppriseUrls.ts
 * @brief TanStack Query hook for the member's Apprise apps.
 */
import { useQuery } from "@tanstack/react-query";
import { listAppriseUrls } from "@/lib/api/apprise";

export const APPRISE_KEY = ["notifications", "apprise"] as const;

/**
 * @brief List the current user's Apprise apps.
 * @return query result
 */
export const useAppriseUrls = () =>
  useQuery({ queryKey: APPRISE_KEY, queryFn: listAppriseUrls });
