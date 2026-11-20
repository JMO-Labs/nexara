/**
 * @file app/app/admin/page.tsx
 * @brief Admin index route: active tab body (frame in layout.tsx).
 */
import { AdminSection } from "@/components/admin/AdminSection";

export const metadata = {
  title: "Admin Panel",
};

export default function AdminPage() {
  return <AdminSection />;
}
