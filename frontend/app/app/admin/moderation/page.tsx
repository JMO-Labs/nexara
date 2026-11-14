/**
 * @file app/app/admin/moderation/page.tsx
 * @brief Moderation queue admin page.
 */
import { ModerationGate } from "@/components/moderation/ModerationGate";

export const metadata = { title: "Moderation" };

export default function ModerationPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-black">Moderation</h1>
        <p className="text-sm text-muted">Review reported content.</p>
      </div>
      <ModerationGate />
    </div>
  );
}
