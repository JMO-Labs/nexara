"use client";
/**
 * @file components/moderation/ModerationGate.tsx
 * @brief Admin-role guard around the moderation queue.
 */
import { AdminNotice } from "@/components/admin/AdminState";
import { useSession } from "@/stores/session";
import { ModerationQueue } from "./ModerationQueue";

/** @brief Renders ModerationQueue for admins only. */
export function ModerationGate() {
  const user = useSession((s) => s.user);
  if (!user || user.role !== "admin")
    return <AdminNotice>Admin access required.</AdminNotice>;
  return <ModerationQueue />;
}
