"use client";
/**
 * @file components/admin/AdminGate.tsx
 * @brief Single admin-role guard for every /app/admin route.
 */
import type { ReactNode } from "react";
import { useSession } from "@/stores/session";
import { isAdmin } from "@/components/layout/navItems";
import { AdminNotice } from "./AdminState";

/**
 * @brief Render children for admins only; otherwise an access notice.
 * @param children admin content
 * @return children or notice
 */
export function AdminGate({ children }: { children: ReactNode }) {
  const user = useSession((s) => s.user);
  if (!isAdmin(user)) {
    return (
      <AdminNotice>
        Admin access required. Your current role is:{" "}
        {user?.role || "unauthenticated"}
      </AdminNotice>
    );
  }
  return <>{children}</>;
}
