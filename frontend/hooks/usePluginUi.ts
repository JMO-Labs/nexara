"use client";
/**
 * @file hooks/usePluginUi.ts
 * @brief Plugins enabled in the viewer's community (prefs + composer flags).
 */
import { useQuery } from "@tanstack/react-query";
import { listPluginUi } from "@/lib/api/plugins";

export function usePluginUi() {
  return useQuery({
    queryKey: ["plugins", "ui"],
    queryFn: listPluginUi,
    staleTime: 5 * 60_000,
  });
}
