"use client";
/**
 * @file components/events/CalendarSubscriptionsPanel.tsx
 * @brief Calendar subscriptions manager UI: list, add, delete, sync.
 *        Aesthetic: rows-as-list (48px), columns = title → url → last-sync → status → interval → sync-now → delete.
 */
import * as React from "react";
import { useTranslations } from "next-intl";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";
import Button from "@mui/joy/Button";
import IconButton from "@mui/joy/IconButton";
import Select from "@mui/joy/Select";
import Option from "@mui/joy/Option";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
import Input from "@mui/joy/Input";
import LinearProgress from "@mui/joy/LinearProgress";
import {
  ArrowPathIcon,
  TrashIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";
import { Modal } from "@/components/ui/Modal";
import {
  useCalendarSubscriptions,
  useAddSubscription,
  useDeleteSubscription,
  useSyncNow,
} from "@/hooks/useCalendarSubscriptions";
import { formatDistanceToNow } from "date-fns";
import type { CalendarSubscription } from "@/lib/api/events";

interface AddFormState {
  title: string;
  sourceUrl: string;
  interval: number;
}

/**
 * @brief Empty state when no subscriptions exist.
 */
function EmptyState({ onAdd }: { onAdd: () => void }) {
  const t = useTranslations();
  return (
    <Stack
      spacing={2}
      sx={{
        alignItems: "center",
        justifyContent: "center",
        py: 6,
        textAlign: "center",
      }}
    >
      <Box
        sx={{
          fontSize: "48px",
          opacity: 0.4,
        }}
      >
        📅
      </Box>
      <Typography level="body-md" color="neutral">
        {t("components.calendar.subscriptions.empty")}
      </Typography>
      <Button
        variant="solid"
        color="primary"
        onClick={onAdd}
        sx={{
          fontWeight: "medium",
        }}
      >
        {t("components.calendar.subscriptions.add")}
      </Button>
    </Stack>
  );
}

/**
 * @brief Status badge indicator.
 */
function StatusBadge({
  error,
  lastSynced,
}: {
  error: string | null;
  lastSynced: string | null;
}) {
  if (error) {
    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          color: "danger.main",
          fontSize: "12px",
        }}
      >
        <ExclamationCircleIcon
          style={{ width: "12px", height: "12px", flexShrink: 0 }}
        />
        <span>Error</span>
      </Box>
    );
  }
  if (!lastSynced) {
    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          color: "warning.main",
          fontSize: "12px",
        }}
      >
        <ClockIcon style={{ width: "12px", height: "12px", flexShrink: 0 }} />
        <span>Pending</span>
      </Box>
    );
  }
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 0.5,
        color: "success.main",
        fontSize: "12px",
      }}
    >
      <CheckCircleIcon
        style={{ width: "12px", height: "12px", flexShrink: 0 }}
      />
      <span>Synced</span>
    </Box>
  );
}

/**
 * @brief Single subscription row (48px tall).
 */
function SubscriptionRow({
  sub,
  onDelete,
  onSync,
  isSyncing,
}: {
  sub: CalendarSubscription;
  onDelete: (id: string) => void;
  onSync: (id: string) => void;
  isSyncing: boolean;
}) {
  const t = useTranslations();
  const [showDelete, setShowDelete] = React.useState(false);
  const [interval, setInterval] = React.useState(sub.sync_interval_minutes);

  const handleDelete = () => {
    onDelete(sub.id);
    setShowDelete(false);
  };

  return (
    <>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr 1.2fr 1fr 0.8fr 0.9fr 40px 40px",
          gap: 1,
          alignItems: "center",
          height: "48px",
          px: 2,
          borderBottom: "1px solid",
          borderColor: "divider",
          "&:hover": {
            backgroundColor: "action.hover",
          },
        }}
      >
        {/* Title */}
        <Typography level="body-sm" noWrap sx={{ fontWeight: "medium" }}>
          {sub.title}
        </Typography>

        {/* URL */}
        <Typography
          level="body-xs"
          sx={{
            fontFamily: "monospace",
            fontSize: "12px",
            color: "neutral.500",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {sub.source_url}
        </Typography>

        {/* Last synced */}
        <Typography
          level="body-xs"
          sx={{
            fontSize: "12px",
            color: "neutral.500",
          }}
        >
          {sub.last_synced_at
            ? formatDistanceToNow(new Date(sub.last_synced_at), {
                addSuffix: true,
              })
            : "—"}
        </Typography>

        {/* Status badge */}
        <StatusBadge error={sub.sync_error} lastSynced={sub.last_synced_at} />

        {/* Sync interval select */}
        <Select
          size="sm"
          value={interval}
          onChange={(_, val) => val && setInterval(val)}
          slotProps={{
            button: {
              sx: {
                fontSize: "12px",
              },
            },
          }}
          sx={{
            minWidth: "80px",
          }}
        >
          <Option value={15}>15 min</Option>
          <Option value={30}>30 min</Option>
          <Option value={60}>1 hr</Option>
          <Option value={180}>3 hrs</Option>
          <Option value={720}>12 hrs</Option>
        </Select>

        {/* Sync now button */}
        <IconButton
          size="sm"
          variant="plain"
          onClick={() => onSync(sub.id)}
          disabled={isSyncing}
          sx={{
            color: "neutral.600",
            "&:hover": {
              color: "primary.main",
            },
          }}
        >
          <ArrowPathIcon style={{ width: "16px", height: "16px" }} />
        </IconButton>

        {/* Delete button */}
        <IconButton
          size="sm"
          variant="plain"
          onClick={() => setShowDelete(true)}
          sx={{
            color: "neutral.600",
            "&:hover": {
              color: "danger.main",
            },
          }}
        >
          <TrashIcon style={{ width: "16px", height: "16px" }} />
        </IconButton>
      </Box>

      {/* Delete confirmation modal */}
      <Modal
        open={showDelete}
        onClose={() => setShowDelete(false)}
        title={t("components.calendar.subscriptions.delete_confirm")}
      >
        <Stack spacing={2}>
          <Typography level="body-sm">
            {t("components.calendar.subscriptions.delete_confirm_text", {
              title: sub.title,
            })}
          </Typography>
          <Stack
            direction="row"
            spacing={1}
            sx={{ justifyContent: "flex-end" }}
          >
            <Button variant="plain" onClick={() => setShowDelete(false)}>
              {t("actions.cancel")}
            </Button>
            <Button variant="solid" color="danger" onClick={handleDelete}>
              {t("actions.delete")}
            </Button>
          </Stack>
        </Stack>
      </Modal>
    </>
  );
}

interface AddModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: {
    title: string;
    source_url: string;
    sync_interval_minutes: number;
  }) => void;
  isLoading: boolean;
}

/**
 * @brief Add subscription modal with form.
 */
function AddModal({ open, onClose, onSubmit, isLoading }: AddModalProps) {
  const t = useTranslations();
  const [form, setForm] = React.useState<AddFormState>({
    title: "",
    sourceUrl: "",
    interval: 60,
  });

  const handleSubmit = () => {
    if (form.title && form.sourceUrl) {
      onSubmit({
        title: form.title,
        source_url: form.sourceUrl,
        sync_interval_minutes: form.interval,
      });
      setForm({ title: "", sourceUrl: "", interval: 60 });
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("components.calendar.subscriptions.add_modal_title")}
    >
      <Stack spacing={2}>
        <FormControl>
          <FormLabel>{t("components.calendar.subscriptions.title")}</FormLabel>
          <Input
            placeholder="e.g., Work Calendar"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            disabled={isLoading}
          />
        </FormControl>

        <FormControl>
          <FormLabel>{t("components.calendar.subscriptions.url")}</FormLabel>
          <Input
            placeholder="https://example.com/calendar.ics"
            value={form.sourceUrl}
            onChange={(e) => setForm({ ...form, sourceUrl: e.target.value })}
            disabled={isLoading}
            slotProps={{
              input: {
                type: "url",
              },
            }}
          />
        </FormControl>

        <FormControl>
          <FormLabel>
            {t("components.calendar.subscriptions.interval")}
          </FormLabel>
          <Select
            value={form.interval}
            onChange={(_, val) => val && setForm({ ...form, interval: val })}
            disabled={isLoading}
          >
            <Option value={15}>Every 15 minutes</Option>
            <Option value={30}>Every 30 minutes</Option>
            <Option value={60}>Every hour</Option>
            <Option value={180}>Every 3 hours</Option>
            <Option value={720}>Every 12 hours</Option>
          </Select>
        </FormControl>

        <Stack
          direction="row"
          spacing={1}
          sx={{ justifyContent: "flex-end", pt: 1 }}
        >
          <Button variant="plain" onClick={onClose} disabled={isLoading}>
            {t("actions.cancel")}
          </Button>
          <Button
            variant="solid"
            color="primary"
            onClick={handleSubmit}
            loading={isLoading}
            disabled={!form.title || !form.sourceUrl}
          >
            {t("actions.add")}
          </Button>
        </Stack>
      </Stack>
    </Modal>
  );
}

/**
 * @brief Main subscriptions panel.
 */
export function CalendarSubscriptionsPanel() {
  const t = useTranslations();
  const [showAddModal, setShowAddModal] = React.useState(false);
  const { data: subscriptions, isLoading } = useCalendarSubscriptions();
  const addMutation = useAddSubscription();
  const deleteMutation = useDeleteSubscription();
  const syncMutation = useSyncNow();

  const handleAdd = (data: Parameters<AddModalProps["onSubmit"]>[0]) => {
    addMutation.mutate(data, {
      onSuccess: () => {
        setShowAddModal(false);
      },
    });
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  const handleSync = (id: string) => {
    syncMutation.mutate(id);
  };

  if (isLoading) {
    return <LinearProgress />;
  }

  const empty = !subscriptions || subscriptions.length === 0;

  return (
    <Stack spacing={2}>
      <div>
        <Typography level="h3" component="h3" sx={{ mb: 0.5 }}>
          {t("components.calendar.subscriptions.title")}
        </Typography>
        <Typography level="body-sm" color="neutral">
          {t("components.calendar.subscriptions.description")}
        </Typography>
      </div>

      {empty ? (
        <EmptyState onAdd={() => setShowAddModal(true)} />
      ) : (
        <Box
          sx={{
            border: "1px solid",
            borderColor: "divider",
            borderRadius: "sm",
            overflow: "hidden",
          }}
        >
          {subscriptions.map((sub) => (
            <SubscriptionRow
              key={sub.id}
              sub={sub}
              onDelete={handleDelete}
              onSync={handleSync}
              isSyncing={
                syncMutation.isPending && syncMutation.variables === sub.id
              }
            />
          ))}
        </Box>
      )}

      {!empty && (
        <Button
          variant="outlined"
          onClick={() => setShowAddModal(true)}
          sx={{
            alignSelf: "flex-start",
          }}
        >
          {t("components.calendar.subscriptions.add")}
        </Button>
      )}

      <AddModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAdd}
        isLoading={addMutation.isPending}
      />
    </Stack>
  );
}
