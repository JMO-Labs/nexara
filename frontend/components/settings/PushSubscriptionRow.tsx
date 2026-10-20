"use client";
/**
 * @file components/settings/PushSubscriptionRow.tsx
 * @brief Push notification opt-in row for the Notifications settings tab.
 *        Shows current permission, lets the user subscribe/unsubscribe.
 */
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Button from "@mui/joy/Button";
import Chip from "@mui/joy/Chip";
import Alert from "@mui/joy/Alert";
import { usePushNotifications } from "@/hooks/usePushNotifications";

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
      <Alert color="neutral" variant="soft">
        Web Push is not supported in this browser.
      </Alert>
    );
  }

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
        <Typography level="title-md">Push notifications</Typography>
        <Chip
          size="sm"
          variant="soft"
          color={isSubscribed ? "success" : "neutral"}
        >
          {isSubscribed ? "Active" : "Inactive"}
        </Chip>
        <Chip size="sm" variant="outlined">
          permission: {permission}
        </Chip>
      </Stack>
      <Typography level="body-sm" color="neutral">
        Receive notifications on this device even when Nexara is closed.
      </Typography>
      <Stack direction="row" spacing={1}>
        {!isSubscribed ? (
          <Button
            variant="solid"
            color="primary"
            loading={isSubscribing}
            onClick={() => subscribe().catch(() => {})}
            disabled={permission === "denied"}
          >
            Enable on this device
          </Button>
        ) : (
          <Button
            variant="outlined"
            color="neutral"
            loading={isUnsubscribing}
            onClick={() => unsubscribe().catch(() => {})}
          >
            Disable on this device
          </Button>
        )}
      </Stack>
      {permission === "denied" && (
        <Alert color="warning" variant="soft">
          Notifications are blocked. Enable them in your browser site settings.
        </Alert>
      )}
      {error && (
        <Alert color="danger" variant="soft" role="alert">
          {error.message}
        </Alert>
      )}
    </Stack>
  );
}
