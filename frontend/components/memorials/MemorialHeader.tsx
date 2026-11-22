"use client";
/**
 * @file components/memorials/MemorialHeader.tsx
 * @brief Calm banner for a remembered person or pet: name, years and a
 *        "Share a memory" button that opens the composer with @handle.
 */
import { Flower2 } from "lucide-react";
import { Button } from "@/components/ui";
import { useModals } from "@/stores/modals";
import { lifespan } from "@/lib/memorial";

export interface MemorialHeaderProps {
  name: string;
  /** Mention handle without the "@" (null hides the button). */
  handle: string | null;
  born?: string | null;
  passedOn?: string | null;
}

/**
 * @param props see MemorialHeaderProps
 * @return banner section
 */
export function MemorialHeader({
  name,
  handle,
  born,
  passedOn,
}: MemorialHeaderProps) {
  const years = lifespan(born, passedOn);
  return (
    <section
      aria-label={`In memory of ${name}`}
      className="flex flex-wrap items-center gap-3 rounded-[20px] border border-[var(--nx-glass-edge)] bg-[var(--nx-glass-solid)] px-5 py-4 text-ink"
    >
      <Flower2 className="size-5 text-muted" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-medium">In loving memory of {name}</p>
        {years && <p className="text-sm text-muted">{years}</p>}
      </div>
      {handle && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            useModals.getState().show("create-post", { text: `@${handle} ` })
          }
        >
          Share a memory
        </Button>
      )}
    </section>
  );
}
