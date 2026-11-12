"use client";
/**
 * @file hooks/useDataExport.ts
 * @brief TanStack Query hooks for the "Download my data" export flow.
 */
import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import {
  getExportStatus,
  listExports,
  requestExport,
  type DataExport,
} from "@/lib/api/dataExport";
import { useToasts } from "@/stores/toasts";

/**
 * @brief Poll one export's status; stops when ready/expired/failed.
 *        Toasts once when it transitions to ready.
 * @param id export id (idle when null)
 * @param intervalMs poll interval, default 2000
 * @return query result
 */
export function useExportStatus(id: string | null, intervalMs = 2000) {
  const push = useToasts((s) => s.push);
  const prev = useRef<string | undefined>(undefined);
  const q = useQuery<DataExport>({
    queryKey: qk.dataExport.status(id ?? ""),
    queryFn: () => getExportStatus(id as string),
    enabled: !!id,
    refetchInterval: (query) => {
      const st = query.state.data?.status;
      return st === "pending" || st === "processing" ? intervalMs : false;
    },
  });
  const status = q.data?.status;
  useEffect(() => {
    const was = prev.current;
    prev.current = status;
    if (status === "ready" && (was === "pending" || was === "processing")) {
      push({
        variant: "success",
        message:
          "Your data export is ready! Download link expires in 48 hours.",
      });
    }
  }, [status, push]);
  return q;
}

/** @brief Mutation requesting a new export. @return mutation */
export function useRequestExport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: requestExport,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: qk.dataExport.history() }),
  });
}

/** @brief Last 5 exports. @return query result */
export function useExportHistory() {
  return useQuery({
    queryKey: qk.dataExport.history(),
    queryFn: () => listExports(5),
  });
}
