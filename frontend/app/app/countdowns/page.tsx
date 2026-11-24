/**
 * @file app/app/countdowns/page.tsx
 * @brief Countdowns list with a create button.
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui";
import { CountdownCard } from "@/components/countdowns/CountdownCard";
import { CountdownComposer } from "@/components/countdowns/CountdownComposer";
import { useCountdowns } from "@/hooks/useCountdowns";

export default function CountdownsRoute() {
  const router = useRouter();
  const { data = [] } = useCountdowns();
  const [open, setOpen] = useState(false);
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Countdowns</h1>
        <Button onClick={() => setOpen(true)}>New countdown</Button>
      </div>
      {data.length === 0 ? <p>No countdowns yet.</p> : null}
      {data.map((c) => (
        <CountdownCard key={c.id} c={c} />
      ))}
      {open ? (
        <CountdownComposer
          open
          onClose={() => setOpen(false)}
          onCreated={(c) => router.push(`/app/countdowns/${c.id}`)}
        />
      ) : null}
    </main>
  );
}
