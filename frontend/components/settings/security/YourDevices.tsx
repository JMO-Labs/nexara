"use client";
/**
 * @file components/settings/security/YourDevices.tsx
 * @brief Signed-in devices (refresh-token families) with per-device sign-out
 *        and "Sign out everywhere else".
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, LogOut } from "lucide-react";
import { Button, IconButton } from "@/components/ui";
import { formatApiError } from "@/lib/api/errors";
import {
  listSessions,
  revokeOtherSessions,
  revokeSession,
  type DeviceSession,
} from "@/lib/api/signins";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useToasts } from "@/stores/toasts";

const KEY = ["sessions"];
// ponytail: mirrors backend ACCESS_TOKEN_EXPIRE_MINUTES default; no config endpoint exposes it.
const ACCESS_MINUTES = 15;

/** @brief Device list for Settings › Security. */
export function YourDevices() {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const confirm = useConfirmDialog((s) => s.confirm);
  const list = useQuery({ queryKey: KEY, queryFn: listSessions });
  const opts = {
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
    onError: (e: unknown) =>
      push({ variant: "danger", message: formatApiError(e) }),
  };
  const remove = useMutation({ mutationFn: revokeSession, ...opts });
  const others = useMutation({ mutationFn: revokeOtherSessions, ...opts });
  const rows = list.data ?? [];
  const busyId = remove.isPending ? remove.variables : undefined;

  const signOut = async (d: DeviceSession) => {
    const ok = await confirm({
      title: "Sign out this device?",
      message: `${d.device} will be signed out.`,
      confirmLabel: "Sign out",
      tone: "danger",
    });
    if (ok) remove.mutate(d.family_id);
  };
  const signOutOthers = async () => {
    const ok = await confirm({
      title: "Sign out everywhere else?",
      message: "Every other device will need to sign in again.",
      confirmLabel: "Sign out all",
      tone: "danger",
    });
    if (ok) others.mutate();
  };

  if (list.isError)
    return (
      <p role="alert" className="text-sm text-destructive">
        Could not load devices.
      </p>
    );
  if (list.isPending)
    return (
      <p role="status" className="text-sm text-muted">
        Loading devices…
      </p>
    );
  return (
    <div className="flex flex-col gap-3">
      <ul className="space-y-2">
        {rows.map((d) => (
          <li key={d.family_id} className="flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {d.device}
                {d.current && (
                  <span className="ml-2 text-xs text-muted">This device</span>
                )}
              </p>
              <p className="text-xs text-muted">
                {d.ip ? `${d.ip} · ` : ""}Last active{" "}
                {new Date(d.last_seen).toLocaleString()}
              </p>
            </div>
            {!d.current && (
              <IconButton
                aria-label={`Sign out ${d.device}`}
                aria-busy={busyId === d.family_id || undefined}
                disabled={busyId === d.family_id}
                onClick={() => signOut(d)}
              >
                {busyId === d.family_id ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                ) : (
                  <LogOut className="size-4" aria-hidden="true" />
                )}
              </IconButton>
            )}
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted">
        Signed-out devices stop working within {ACCESS_MINUTES} minutes.
      </p>
      {rows.some((d) => !d.current) && (
        <div>
          <Button
            variant="ghost"
            onClick={signOutOthers}
            loading={others.isPending}
          >
            Sign out everywhere else
          </Button>
        </div>
      )}
    </div>
  );
}
