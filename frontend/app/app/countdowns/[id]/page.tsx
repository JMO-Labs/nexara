/**
 * @file app/app/countdowns/[id]/page.tsx
 * @brief Countdown detail: card, edit title/date, delete.
 */
"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Input } from "@/components/ui";
import { CountdownCard } from "@/components/countdowns/CountdownCard";
import {
  useCountdown,
  useDeleteCountdown,
  useUpdateCountdown,
} from "@/hooks/useCountdowns";
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
  const update = useUpdateCountdown(id);
  const del = useDeleteCountdown();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");

  if (isError) return <p role="alert">Countdown not found.</p>;
  if (!c) return null;
  const mine = me?.id === c.author_id;
  const admin = me?.role === "admin" || me?.role === "owner";

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
      {editing ? (
        <div className="flex flex-col gap-3">
          <Input
            label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Input
            label="Date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <div className="flex gap-2">
            <Button
              disabled={!title.trim() || !date || update.isPending}
              onClick={() =>
                update.mutate(
                  { title: title.trim(), target_date: date },
                  { onSuccess: () => setEditing(false) },
                )
              }
            >
              Save
            </Button>
            <Button variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          {mine ? (
            <Button
              variant="secondary"
              onClick={() => {
                setTitle(c.title);
                setDate(c.target_date);
                setEditing(true);
              }}
            >
              Edit
            </Button>
          ) : null}
          {mine || admin ? (
            <Button variant="destructive" onClick={remove}>
              Delete
            </Button>
          ) : null}
        </div>
      )}
    </main>
  );
}
