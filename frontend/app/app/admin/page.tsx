/**
 * @file app/app/admin/page.tsx
 * @brief Admin panel server page wrapper.
 */
import Link from "next/link";
import { AdminTabs } from "@/components/admin/AdminTabs";

export const metadata = {
  title: "Admin Panel",
};

export default function AdminPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-black">Admin panel</h1>
        <p className="text-sm text-muted">
          Manage community, users, settings, and integrations.
        </p>
        <Link href="/app/admin/storage" className="text-sm underline">
          Storage analytics
        </Link>
      </div>
      <AdminTabs />
    </div>
  );
}
