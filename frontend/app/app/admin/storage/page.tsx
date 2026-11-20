/**
 * @file app/app/admin/storage/page.tsx
 * @brief Admin storage analytics page (frame and admin gate in admin/layout.tsx).
 */
import { StorageView } from "@/components/admin/StorageView";

export const metadata = { title: "Storage analytics" };

export default function AdminStoragePage() {
  return <StorageView />;
}
