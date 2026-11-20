"use client";
/**
 * @file app/app/admin/plugins/[id]/page.tsx
 * @brief Plugin detail page (frame and admin gate in admin/layout.tsx).
 */
import { use } from "react";
import { PluginDetail } from "@/components/admin/PluginDetail";

export default function PluginDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <PluginDetail id={id} />;
}
