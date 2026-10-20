"use client";
/**
 * @file components/settings/PushSubscriptionRow.tsx
 * @brief Push notification opt-in row for the Notifications settings tab.
 *        Shows current permission, lets the user subscribe/unsubscribe.
 */
import { Button, Badge, Card } from "@/components/ui";
import { usePushNotifications } from "@/hooks/usePushNotifications";

const alertCls = "rounded-2xl bg-surface p-3 text-sm border-l-4";

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
      <div role="status" className={`${alertCls} border-muted`}>
        Web Push is not supported in this browser.
      </div>
    );
  }

  return (
    <Card className="max-w-3xl space-y-3 p-4 md:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">Push notifications</h2>
        <Badge tone={isSubscribed ? "leaf" : "neutral"}>
          {isSubscribed ? "Active" : "Inactive"}
        </Badge>
        <Badge>permission: {permission}</Badge>
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
            variant="outline"
            loading={isUnsubscribing}
            onClick={() => unsubscribe().catch(() => {})}
          >
            Disable on this device
          </Button>
        )}
      </div>
      {permission === "denied" && (
        <div role="alert" className={`${alertCls} border-sun`}>
          Notifications are blocked. Enable them in your browser site settings.
        </div>
      )}
      {error && (
        <div role="alert" className={`${alertCls} border-destructive`}>
          {error.message}
        </div>
      )}
    </Card>
  );
}
