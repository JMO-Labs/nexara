"use client";
/**
 * @file components/settings/security/PasskeyList.tsx
 * @brief Lists registered passkeys with add / rename / remove. Hidden behind a
 *        note when the page is not a secure context.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { Button, IconButton, Input } from "@/components/ui";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import {
  deletePasskey,
  listPasskeys,
  renamePasskey,
} from "@/lib/api/twoFactor";
import { passkeysAvailable, registerPasskey } from "@/lib/passkeys";

const KEY = ["2fa", "passkeys"];
const STATUS = ["2fa", "status"];

/** @brief Passkey management list. */
export function PasskeyList() {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const confirm = useConfirmDialog((s) => s.confirm);
  const secure = passkeysAvailable();
  const [editing, setEditing] = useState<string | null>(null);
  const [name, setName] = useState("");
  const list = useQuery({
    queryKey: KEY,
    queryFn: listPasskeys,
    enabled: secure,
  });
  const fail = (e: unknown) =>
    push({ variant: "danger", message: formatApiError(e) });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: KEY });
    qc.invalidateQueries({ queryKey: STATUS });
  };
  const add = useMutation({
    mutationFn: () =>
      registerPasskey(`Passkey ${(list.data?.length ?? 0) + 1}`),
    onSuccess: refresh,
    onError: fail,
  });
  const rename = useMutation({
    mutationFn: (v: { id: string; name: string }) =>
      renamePasskey(v.id, v.name),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
    onError: fail,
  });
  const remove = useMutation({
    mutationFn: deletePasskey,
    onSuccess: refresh,
    onError: fail,
  });

  if (!secure)
    return (
      <p className="text-sm text-muted">
        Passkeys need a secure (HTTPS) connection.
      </p>
    );
  const onRemove = async (id: string, label: string) => {
    const ok = await confirm({
      title: "Remove passkey?",
      message: `${label} will no longer sign you in.`,
      confirmLabel: "Remove",
      tone: "danger",
    });
    if (ok) remove.mutate(id);
  };
  return (
    <div className="flex flex-col gap-3">
      {list.data && list.data.length === 0 && (
        <p className="text-sm text-muted">No passkeys yet.</p>
      )}
      <ul className="space-y-2">
        {(list.data ?? []).map((p) => (
          <li key={p.id} className="flex items-center gap-2">
            {editing === p.id ? (
              <form
                className="flex flex-1 items-end gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (name.trim())
                    rename.mutate({ id: p.id, name: name.trim() });
                }}
              >
                <Input
                  label="Passkey name"
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <Button type="submit" loading={rename.isPending}>
                  Save
                </Button>
              </form>
            ) : (
              <>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-muted">
                    {p.last_used_at
                      ? `Last used ${new Date(p.last_used_at).toLocaleDateString()}`
                      : "Never used"}
                  </p>
                </div>
                <IconButton
                  aria-label={`Rename ${p.name}`}
                  onClick={() => {
                    setEditing(p.id);
                    setName(p.name);
                  }}
                >
                  <Pencil className="size-4" aria-hidden="true" />
                </IconButton>
                <IconButton
                  aria-label={`Remove ${p.name}`}
                  onClick={() => onRemove(p.id, p.name)}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </IconButton>
              </>
            )}
          </li>
        ))}
      </ul>
      <Button
        className="self-start"
        loading={add.isPending}
        onClick={() => add.mutate()}
      >
        Add a passkey
      </Button>
    </div>
  );
}
