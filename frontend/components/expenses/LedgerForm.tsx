"use client";
/**
 * @file components/expenses/LedgerForm.tsx
 * @brief Create a shared-costs ledger: name, people, optional event/wishlist link.
 */
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { useMembersList } from "@/hooks/useMembersList";
import { createLedger, type Ledger } from "@/lib/api/expenses";
import { formatApiError } from "@/lib/api/errors";
import { useSession } from "@/stores/session";
import { MemberPicker } from "./MemberPicker";

/**
 * @brief New ledger form.
 * @param eventId link the ledger to this event
 * @param wishlistId link the ledger to this wishlist
 * @param defaultName initial name
 * @param onCreated called with the new ledger
 * @return form
 */
export function LedgerForm({
  eventId,
  wishlistId,
  defaultName = "",
  onCreated,
}: {
  eventId?: string;
  wishlistId?: string;
  defaultName?: string;
  onCreated: (l: Ledger) => void;
}) {
  const me = useSession((s) => s.user?.id);
  const { data: members = [] } = useMembersList();
  const [name, setName] = useState(defaultName);
  const [ids, setIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return setError("Give the ledger a name");
    setBusy(true);
    setError(undefined);
    try {
      onCreated(
        await createLedger({
          name: name.trim(),
          event_id: eventId ?? null,
          wishlist_id: wishlistId ?? null,
          member_ids: ids,
        }),
      );
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <Input
        label="Name"
        value={name}
        maxLength={80}
        onChange={(e) => setName(e.target.value)}
        error={error}
        placeholder="Beach house weekend"
      />
      <MemberPicker
        legend="Who is sharing costs? (you are included)"
        people={members.filter((m) => m.id !== me)}
        value={ids}
        onChange={setIds}
      />
      <Button type="submit" loading={busy}>
        Create ledger
      </Button>
    </form>
  );
}
