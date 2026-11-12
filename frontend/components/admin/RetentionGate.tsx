"use client";
/**
 * @file components/admin/RetentionGate.tsx
 * @brief Admin-role guard around the retention tab.
 */
import { useSession } from "@/stores/session";
import { AdminNotice } from "./AdminState";
import { RetentionTab } from "./RetentionTab";

/** @brief Renders RetentionTab for admins only. */
export function RetentionGate() {
  const user = useSession((s) => s.user);
  if (!user || user.role !== "admin") {
    return <AdminNotice>Admin access required.</AdminNotice>;
  }
  return <RetentionTab />;
}
