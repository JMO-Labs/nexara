/**
 * @file app/app/admin/storage/page.tsx
 * @brief Admin storage analytics page.
 */
import { StorageView } from "@/components/admin/StorageView";

export const metadata = { title: "Storage analytics" };

export default function AdminStoragePage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-black">Storage analytics</h1>
        <p className="text-sm text-muted">
          Usage trends and per-user breakdown.
        </p>
      </div>
      <StorageView />
    </div>
  );
}
