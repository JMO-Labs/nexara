"use client";
/**
 * @file components/settings/PushSubscriptionRow.tsx
 * @brief Push notification opt-in row for the Notifications settings tab.
 *        Shows current permission, lets the user subscribe/unsubscribe.
 */
import { Button, Badge } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { usePushNotifications } from "@/hooks/usePushNotifications";

const alertCls = "glass-item rounded-[20px] p-3 text-sm";

/**
 * @brief Push subscription controls.
 * @return push opt-in card
 */
export function PushSubscriptionRow() {
  const {
    supported,
    permission,
    isSubscribed,
    subscribe,
    unsubscribe,
    isSubscribing,
    isUnsubscribing,
    error,
  } = usePushNotifications();

  if (!supported) {
    return (
      <div role="status" className={alertCls}>
        Web Push is not supported in this browser.
      </div>
    );
  }

  return (
    <Panel className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">Push notifications</h2>
        <Badge tone={isSubscribed ? "leaf" : "neutral"}>
          {isSubscribed ? "Active" : "Inactive"}
        </Badge>
      </div>
      <p className="text-sm text-muted">
        Receive notifications on this device even when Nexara is closed.
      </p>
      <div>
        {!isSubscribed ? (
          <Button
            loading={isSubscribing}
            onClick={() => subscribe().catch(() => {})}
            disabled={permission === "denied"}
          >
            Enable on this device
          </Button>
        ) : (
          <Button
            variant="secondary"
            loading={isUnsubscribing}
            onClick={() => unsubscribe().catch(() => {})}
          >
            Disable on this device
          </Button>
        )}
      </div>
      {permission === "denied" && (
        <div role="alert" className={alertCls}>
          Notifications are blocked. Enable them in your browser site settings.
        </div>
      )}
      {error && (
        <div role="alert" className={alertCls}>
          {error.message}
        </div>
      )}
    </Panel>
  );
}
