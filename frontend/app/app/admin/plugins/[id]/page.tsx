"use client";
/**
 * @file app/app/admin/plugins/[id]/page.tsx
 * @brief Plugin detail page (admin role required).
 */
import { use } from "react";
import { PluginDetail } from "@/components/admin/PluginDetail";

export default function PluginDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-3xl font-black">Plugin</h1>
      <PluginDetail id={id} />
    </div>
  );
}
