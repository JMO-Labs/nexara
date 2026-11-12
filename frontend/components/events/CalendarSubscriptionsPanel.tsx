"use client";
/**
 * @file components/events/CalendarSubscriptionsPanel.tsx
 * @brief Calendar subscriptions manager: list, add, delete, sync.
 */
import * as React from "react";
import { CalendarDays, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button, EmptyState } from "@/components/ui";
import {
  useCalendarSubscriptions,
  useAddSubscription,
  useUpdateSubscription,
  useDeleteSubscription,
  useSyncNow,
} from "@/hooks/useCalendarSubscriptions";
import { AddModal, type AddModalProps } from "./subscriptions/AddModal";
import { SubscriptionRow } from "./subscriptions/SubscriptionRow";

/**
 * @return subscriptions panel (also mounted by settings)
 */
export function CalendarSubscriptionsPanel() {
  const t = useTranslations();
  const [showAddModal, setShowAddModal] = React.useState(false);
  const { data: subscriptions, isLoading } = useCalendarSubscriptions();
  const addMutation = useAddSubscription();
  const updateMutation = useUpdateSubscription();
  const deleteMutation = useDeleteSubscription();
  const syncMutation = useSyncNow();

  const handleAdd = (data: Parameters<AddModalProps["onSubmit"]>[0]) => {
    addMutation.mutate(data, { onSuccess: () => setShowAddModal(false) });
  };

  if (isLoading) {
    return (
      <div role="status" aria-label="Loading" className="p-4">
        <Loader2 aria-hidden className="size-5 motion-safe:animate-spin" />
      </div>
    );
  }

  const empty = !subscriptions || subscriptions.length === 0;
  const addLabel = t("components.calendar.subscriptions.add");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-lg font-semibold">
          {t("components.calendar.subscriptions.title")}
        </h3>
        <p className="text-sm text-muted">
          {t("components.calendar.subscriptions.description")}
        </p>
      </div>

      {empty ? (
        <EmptyState
          icon={CalendarDays}
          compact
          title={t("components.calendar.subscriptions.empty")}
          action={
            <Button onClick={() => setShowAddModal(true)}>{addLabel}</Button>
          }
        />
      ) : (
        <>
          <div className="overflow-hidden rounded-2xl bg-surface">
            {subscriptions.map((sub) => (
              <SubscriptionRow
                key={sub.id}
                sub={sub}
                onDelete={(id) => deleteMutation.mutate(id)}
                onUpdate={(id, body) => updateMutation.mutate({ id, body })}
                onSync={(id) => syncMutation.mutate(id)}
                isSyncing={
                  syncMutation.isPending && syncMutation.variables === sub.id
                }
              />
            ))}
          </div>
          <Button
            variant="outline"
            className="self-start"
            onClick={() => setShowAddModal(true)}
          >
            {addLabel}
          </Button>
        </>
      )}

      <AddModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAdd}
        isLoading={addMutation.isPending}
      />
    </div>
  );
}
