/**
 * @file app/app/countdowns/[id]/page.tsx
 * @brief Countdown detail: card, edit title/date, delete.
 */
"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui";
import { CountdownComposer } from "@/components/countdowns/CountdownComposer";
import { CountdownCard } from "@/components/countdowns/CountdownCard";
import { useCountdown, useDeleteCountdown } from "@/hooks/useCountdowns";
import { useSession } from "@/stores/session";
import { useConfirmDialog } from "@/stores/confirmDialog";

export default function CountdownRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const me = useSession((s) => s.user);
  const confirm = useConfirmDialog((s) => s.confirm);
  const { data: c, isError } = useCountdown(id);
  const del = useDeleteCountdown();
  const [editing, setEditing] = useState(false);

  if (isError) return <p role="alert">Countdown not found.</p>;
  if (!c) return null;
  const mine = me?.id === c.author_id;
  const admin = me?.role === "admin";

  const remove = async () => {
    const ok = await confirm({
      title: "Delete countdown?",
      message: "This countdown will be permanently deleted.",
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (ok) del.mutate(id, { onSuccess: () => router.push("/app") });
  };

  return (
    <main className="mx-auto flex max-w-xl flex-col gap-4 p-4">
      <CountdownCard c={c} />
      <div className="flex gap-2">
        {mine ? (
          <Button variant="secondary" onClick={() => setEditing(true)}>
            Edit
          </Button>
        ) : null}
        {mine || admin ? (
          <Button variant="destructive" onClick={remove}>
            Delete
          </Button>
        ) : null}
      </div>
      {editing ? (
        <CountdownComposer
          open
          countdown={c}
          onClose={() => setEditing(false)}
        />
      ) : null}
    </main>
  );
}
