"use client";
/**
 * @file components/feed/InterestPrompt.tsx
 * @brief "Add to your interests?" card shown after an interest-capture reply.
 */
import { Button, Chip } from "@/components/ui";

/**
 * @param slug interest category slug
 * @param busy add request in flight
 * @param onAdd add handler
 * @param onDismiss dismiss handler
 * @return status card
 */
export function InterestPrompt({
  slug,
  busy,
  onAdd,
  onDismiss,
}: {
  slug?: string;
  busy: boolean;
  onAdd: () => void;
  onDismiss: () => void;
}) {
  return (
    <div
      role="status"
      className="bg-surface text-ink mt-2 flex flex-col items-start gap-2 rounded-2xl border border-muted/40 p-3"
    >
      <p className="text-sm font-semibold">Add to your interests?</p>
      {slug && <Chip tone="accent">{slug}</Chip>}
      <div className="flex gap-2">
        <Button size="sm" loading={busy} onClick={onAdd}>
          Add
        </Button>
        <Button size="sm" variant="ghost" onClick={onDismiss}>
          Not now
        </Button>
      </div>
    </div>
  );
}
