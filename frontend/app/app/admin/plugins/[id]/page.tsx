"use client";
/**
 * @file app/app/admin/plugins/[id]/page.tsx
 * @brief Plugin detail (frame and admin gate in admin/layout.tsx).
 */
import { useParams } from "next/navigation";
import { PluginDetail } from "@/components/admin/plugins/PluginDetail";

export default function PluginDetailPage() {
  const { id } = useParams<{ id: string }>();
  return <PluginDetail pluginId={decodeURIComponent(id)} />;
}
