/**
 * @file app/app/admin/retention/page.tsx
 * @brief Retention policy admin page (admin role required).
 */
import { RetentionGate } from "@/components/admin/RetentionGate";

export const metadata = { title: "Data retention" };

export default function RetentionPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-black">Data retention</h1>
        <p className="text-sm text-muted">
          Control how long each type of content is kept.
        </p>
      </div>
      <RetentionGate />
    </div>
  );
}
