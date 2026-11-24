"use client";
/**
 * @file components/countdowns/CountdownComposer.tsx
 * @brief Create-countdown modal: title, date/time, emoji, cover, scope, yearly.
 */
import * as React from "react";
import { Button, Input, Modal, Switch } from "@/components/ui";
import { ScopeSelect, type ScopeValue } from "@/components/ui/ScopeSelect";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useMediaUpload } from "@/hooks/useMediaUpload";
import { useCreateCountdown } from "@/hooks/useCountdowns";
import type { Countdown } from "@/lib/api/countdowns";

const EMOJIS = ["🎉", "🎂", "✈️", "🎄", "🏖️", "💍", "🎓", "⭐"];

export interface CountdownComposerProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (c: Countdown) => void;
}

/**
 * @brief Countdown composer modal.
 * @param open visibility
 * @param onClose cancel/after-create callback
 * @param onCreated receives the new countdown
 * @return modal
 */
export function CountdownComposer({
  open,
  onClose,
  onCreated,
}: CountdownComposerProps) {
  const [title, setTitle] = React.useState("");
  const [date, setDate] = React.useState("");
  const [time, setTime] = React.useState("");
  const [emoji, setEmoji] = React.useState("");
  const [cover, setCover] = React.useState<string | null>(null);
  const [yearly, setYearly] = React.useState(false);
  const [scope, setScope] = React.useState<ScopeValue>({
    visibility: "community",
    subgroup_id: null,
  });
  const groups = useSubgroupList().data ?? [];
  const upload = useMediaUpload();
  const create = useCreateCountdown();
  const valid =
    title.trim() &&
    date &&
    (scope.visibility !== "subgroup" || scope.subgroup_id);

  const submit = () =>
    create.mutate(
      {
        title: title.trim(),
        target_date: date,
        ...(time ? { target_time: time } : {}),
        tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
        ...(emoji ? { emoji } : {}),
        ...(cover ? { cover_media_id: cover } : {}),
        repeat_yearly: yearly,
        visibility: scope.visibility,
        subgroup_id: scope.subgroup_id,
      },
      {
        onSuccess: (c) => {
          onCreated?.(c);
          onClose();
        },
      },
    );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New countdown"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!valid || create.isPending}>
            Create
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Input
          label="Title"
          maxLength={120}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <Input
          label="Date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <Input
          label="Time (optional)"
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
        />
        <div className="flex flex-col gap-1.5">
          <Input
            label="Emoji"
            maxLength={8}
            value={emoji}
            onChange={(e) => setEmoji(e.target.value)}
          />
          <div
            className="flex flex-wrap gap-1"
            role="group"
            aria-label="Emoji suggestions"
          >
            {EMOJIS.map((e) => (
              <Button
                key={e}
                variant="ghost"
                size="sm"
                aria-label={`Use ${e}`}
                onClick={() => setEmoji(e)}
              >
                {e}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="cd-cover" className="text-sm font-medium">
            Cover image (optional)
          </label>
          <input
            id="cd-cover"
            type="file"
            accept="image/*"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (f) setCover(await upload.mutateAsync(f));
            }}
          />
          {cover ? <span className="text-sm">Cover attached</span> : null}
        </div>
        <ScopeSelect value={scope} onChange={setScope} subgroups={groups} />
        <label className="flex items-center justify-between gap-2 text-sm">
          Repeats every year
          <Switch
            aria-label="Repeats every year"
            checked={yearly}
            onCheckedChange={setYearly}
          />
        </label>
      </div>
    </Modal>
  );
}
