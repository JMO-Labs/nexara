"use client";
/**
 * @file components/settings/PushDevices.tsx
 * @brief Push notification devices for the Notifications settings tab:
 *        enable/disable this device, rename and remove devices.
 */
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { Button, Badge, IconButton, Input, SettingsRow } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { iosSafari, standalone } from "@/components/layout/InstallPrompt";
import { useMutationWithToast } from "@/hooks/useMutationWithToast";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import {
  removePushDevice,
  renamePushDevice,
  type PushDevice,
} from "@/lib/api/push";

const alertCls = "glass-item rounded-[20px] p-3 text-sm";

function DeviceRow({
  d,
  mine,
  onRemove,
}: {
  d: PushDevice;
  mine: boolean;
  onRemove: () => void;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(d.name);
  const rename = useMutationWithToast<PushDevice, Error, string>({
    mutationFn: (n) => renamePushDevice(d.id, n),
    successKey: "toasts.settings.saved",
    onSuccess: () => {
      setEditing(false);
      qc.invalidateQueries({ queryKey: ["push"] });
    },
  });
  return (
    <li className="flex flex-wrap items-center gap-2 py-2">
      {editing ? (
        <form
          className="flex flex-1 items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) rename.mutate(name.trim());
          }}
        >
          <Input
            label="Device name"
            value={name}
            maxLength={60}
            onChange={(e) => setName(e.target.value)}
          />
          <Button type="submit" size="sm" loading={rename.isPending}>
            Save
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setEditing(false)}
          >
            Cancel
          </Button>
        </form>
      ) : (
        <>
          <span className="flex-1 truncate text-sm">{d.name}</span>
          {mine && <Badge tone="leaf">This device</Badge>}
          <IconButton
            size="sm"
            variant="ghost"
            aria-label={`Rename ${d.name}`}
            onClick={() => setEditing(true)}
          >
            <Pencil aria-hidden className="size-4" />
          </IconButton>
          <IconButton
            size="sm"
            variant="ghost"
            aria-label={`Remove ${d.name}`}
            onClick={onRemove}
          >
            <Trash2 aria-hidden className="size-4" />
          </IconButton>
        </>
      )}
    </li>
  );
}

/**
 * @brief Push devices panel.
 * @return push opt-in + device list card
 */
export function PushDevices() {
  const qc = useQueryClient();
  const p = usePushNotifications();
  const remove = useMutationWithToast<void, Error, PushDevice>({
    mutationFn: async (d) => {
      if (d.endpoint_hash === p.thisHash) await p.unsubscribe();
      else await removePushDevice(d.id);
    },
    successKey: "toasts.settings.saved",
    onSuccess: () => qc.invalidateQueries({ queryKey: ["push"] }),
  });

  if (typeof window !== "undefined" && iosSafari() && !standalone()) {
    return (
      <Panel className="space-y-3">
        <h2 className="text-lg font-semibold">Push notifications</h2>
        <p role="status" className="text-sm text-muted">
          On iPhone, add Nexara to your Home Screen first to get notifications.
        </p>
      </Panel>
    );
  }
  if (!p.supported) {
    return (
      <div role="status" className={alertCls}>
        Web Push is not supported in this browser.
      </div>
    );
  }

  return (
    <Panel className="space-y-3">
      <h2 className="text-lg font-semibold">Push notifications</h2>
      <p className="text-sm text-muted">
        Receive notifications on your devices even when Nexara is closed.
      </p>
      <SettingsRow label="This device">
        <div className="flex flex-wrap items-center gap-2">
          {p.isSubscribed ? (
            <>
              <Badge tone="leaf">Active</Badge>
              <Button
                variant="secondary"
                loading={p.isUnsubscribing}
                onClick={() => p.unsubscribe().catch(() => {})}
              >
                Turn off for this device
              </Button>
            </>
          ) : (
            <Button
              loading={p.isSubscribing}
              disabled={p.permission === "denied"}
              onClick={() => p.subscribe().catch(() => {})}
            >
              Turn on for this device
            </Button>
          )}
        </div>
      </SettingsRow>
      {p.devices.length > 0 && (
        <ul
          aria-label="Push devices"
          className="divide-y divide-[var(--nx-glass-edge)]"
        >
          {p.devices.map((d) => (
            <DeviceRow
              key={d.id}
              d={d}
              mine={d.endpoint_hash === p.thisHash}
              onRemove={() => remove.mutate(d)}
            />
          ))}
        </ul>
      )}
      {p.permission === "denied" && (
        <div role="alert" className={alertCls}>
          Notifications are blocked. Enable them in your browser site settings.
        </div>
      )}
      {p.error && (
        <div role="alert" className={alertCls}>
          {p.error.message}
        </div>
      )}
    </Panel>
  );
}
