/**
 * @file app/app/admin/moderation/page.tsx
 * @brief Moderation queue admin page (frame and admin gate in admin/layout.tsx).
 */
import { Panel } from "@/components/ui/page";
import { ModerationQueue } from "@/components/moderation/ModerationQueue";

export const metadata = { title: "Moderation" };

export default function ModerationPage() {
  return (
    <Panel as="div">
      <ModerationQueue />
    </Panel>
  );
}
