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
import { useCreateCountdown, useUpdateCountdown } from "@/hooks/useCountdowns";
import type { Countdown } from "@/lib/api/countdowns";

/** @brief Today as YYYY-MM-DD in the browser's timezone. */
const localISODate = () => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

const EMOJIS = ["🎉", "🎂", "✈️", "🎄", "🏖️", "💍", "🎓", "⭐"];

export interface CountdownComposerProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (c: Countdown) => void;
  /** Edit mode: prefill; scope is fixed after creation. */
  countdown?: Countdown;
}

/**
 * @brief Countdown composer modal.
 * @param open visibility
 * @param onClose cancel/after-create callback
 * @param onCreated receives the new countdown (create only)
 * @return modal
 */
export function CountdownComposer({
  open,
  onClose,
  onCreated,
  countdown,
}: CountdownComposerProps) {
  const [title, setTitle] = React.useState(countdown?.title ?? "");
  const [date, setDate] = React.useState(countdown?.target_date ?? "");
  const [time, setTime] = React.useState(
    countdown?.target_time?.slice(0, 5) ?? "",
  );
  const [emoji, setEmoji] = React.useState(countdown?.emoji ?? "");
  const [cover, setCover] = React.useState<string | null>(
    countdown?.cover_media_id ?? null,
  );
  const [coverErr, setCoverErr] = React.useState(false);
  const [yearly, setYearly] = React.useState(countdown?.repeat_yearly ?? false);
  const [scope, setScope] = React.useState<ScopeValue>({
    visibility: "community",
    subgroup_id: null,
  });
  const groups = useSubgroupList().data ?? [];
  const upload = useMediaUpload();
  const create = useCreateCountdown();
  const save = useUpdateCountdown(countdown?.id ?? "");
  const editing = !!countdown;
  const busy = create.isPending || save.isPending || upload.isPending;
  const valid =
    title.trim() &&
    date &&
    (editing || scope.visibility !== "subgroup" || scope.subgroup_id);

  const submit = () => {
    // Edit sends explicit nulls so emptied fields are cleared server-side.
    const opt = <T,>(v: T | "" | null) => (v ? v : editing ? null : undefined);
    const body = {
      title: title.trim(),
      target_date: date,
      target_time: opt(time),
      tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
      emoji: opt(emoji),
      cover_media_id: opt(cover),
      repeat_yearly: yearly,
    };
    const done = {
      onSuccess: (c: Countdown) => {
        if (!editing) onCreated?.(c);
        onClose();
      },
    };
    if (countdown) {
      save.mutate(body, done);
    } else {
      create.mutate(
        {
          ...body,
          visibility: scope.visibility,
          subgroup_id: scope.subgroup_id,
        },
        done,
      );
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? "Edit countdown" : "New countdown"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!valid || busy}>
            {editing ? "Save" : "Create"}
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
          min={editing || yearly ? undefined : localISODate()}
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
                aria-pressed={emoji === e}
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
              if (!f) return;
              setCoverErr(false);
              try {
                setCover(await upload.mutateAsync(f));
              } catch {
                setCoverErr(true);
              }
            }}
          />
          {upload.isPending ? (
            <span className="text-sm">Uploading...</span>
          ) : null}
          {coverErr ? (
            <span role="alert" className="text-sm text-red-700">
              Cover upload failed. Try again.
            </span>
          ) : null}
          {cover && !upload.isPending ? (
            <span className="flex items-center gap-2 text-sm">
              Cover attached
              <Button variant="ghost" size="sm" onClick={() => setCover(null)}>
                Remove cover
              </Button>
            </span>
          ) : null}
        </div>
        {editing ? null : (
          <ScopeSelect value={scope} onChange={setScope} subgroups={groups} />
        )}
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
