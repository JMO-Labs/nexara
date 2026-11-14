"use client";
/**
 * @file hooks/useModeration.ts
 * @brief TanStack Query hooks for the admin moderation queue.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listReports,
  reportAction,
  type ReportActionType,
} from "@/lib/api/moderation";

const KEY = ["admin", "moderation", "reports"] as const;

/** @brief Pending reports. @return query result */
export function useReports() {
  return useQuery({ queryKey: KEY, queryFn: () => listReports("pending") });
}

/** @brief Mutation applying an action to one report. @return mutation */
export function useReportAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; action: ReportActionType; note?: string }) =>
      reportAction(v.id, v.action, v.note),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
