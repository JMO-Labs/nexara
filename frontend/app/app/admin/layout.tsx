/**
 * @file app/app/admin/layout.tsx
 * @brief Shared admin frame (gate, header, section nav) for all admin routes.
 */
import type { ReactNode } from "react";
import { AdminShell } from "@/components/admin/AdminShell";

/**
 * @brief Admin layout.
 * @param children active admin route
 * @return gated admin shell
 */
export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
