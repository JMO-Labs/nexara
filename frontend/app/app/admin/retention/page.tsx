/**
 * @file app/app/admin/retention/page.tsx
 * @brief Retention policy admin page (frame and admin gate in admin/layout.tsx).
 */
import { RetentionTab } from "@/components/admin/RetentionTab";
export const metadata = { title: "Data retention" };
export default function RetentionPage() {
  return <RetentionTab />;
}
