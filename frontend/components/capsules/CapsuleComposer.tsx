"use client";
/**
 * @file components/capsules/CapsuleComposer.tsx
 * @brief Seal a time capsule: title, message, photos, open date (tomorrow or
 *        later) and recipients (everyone, people, groups, household).
 */
import * as React from "react";
import { X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Input, Modal, Textarea } from "@/components/ui";
import { Field, selectCls } from "@/components/wishlists/wizard/fields";
import {
  MediaTray,
  useMediaUploads,
} from "@/components/feed/ComposerAttachments";
import { useMembersList } from "@/hooks/useMembersList";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useVisibleHousehold } from "@/hooks/useHousehold";
import { createCapsule, type RecipientKind } from "@/lib/api/capsules";

interface Pick {
  kind: RecipientKind;
  id: string;
  label: string;
}

/** @return YYYY-MM-DD for tomorrow (local), the earliest open date. */
export function tomorrow(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/**
 * @param open modal visibility
 * @param onClose close handler
 * @return modal composer
 */
export function CapsuleComposer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { data: members = [] } = useMembersList();
  const { data: groups = [] } = useSubgroupList();
  const { data: household = [] } = useVisibleHousehold();
  const uploads = useMediaUploads();
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [title, setTitle] = React.useState("");
  const [body, setBody] = React.useState("");
  const [date, setDate] = React.useState("");
  const [picks, setPicks] = React.useState<Pick[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const save = useMutation({
    mutationFn: () =>
      createCapsule({
        title: title.trim(),
        body,
        media_ids: uploads.readyIds,
        // Local midnight of the chosen day, sent as UTC.
        open_at: new Date(`${date}T00:00:00`).toISOString(),
        recipients: picks.map((p) => ({
          kind: p.kind,
          target_id: p.kind === "community" ? null : p.id,
        })),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["capsules"] });
      onClose();
    },
    onError: () => setError("Could not seal the capsule. Please try again."),
  });

  const add = (v: string) => {
    const [kind, id] = v.split(":") as [RecipientKind, string];
    if (!kind || picks.some((p) => p.kind === kind && p.id === id)) return;
    const label =
      kind === "community"
        ? "Everyone"
        : kind === "user"
          ? (members.find((m) => m.id === id)?.display_name ?? "Someone")
          : kind === "subgroup"
            ? (groups.find((g) => g.id === id)?.name ?? "A group")
            : (household.find((h) => h.id === id)?.name ??
              "A household member");
    setPicks([...picks, { kind, id, label }]);
  };

  const submit = () => {
    setError(null);
    if (!title.trim()) return setError("Add a title.");
    if (!date || date < tomorrow())
      return setError("Pick an open date from tomorrow onward.");
    if (picks.length === 0) return setError("Choose who it is for.");
    save.mutate();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Seal a time capsule"
      description="A message that stays hidden from everyone but you until the open date."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            loading={save.isPending}
            disabled={uploads.busy}
          >
            Seal capsule
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Field label="Title">
          <Input
            value={title}
            maxLength={120}
            onChange={(e) => setTitle(e.target.value)}
          />
        </Field>
        <Field label="Message">
          <Textarea
            rows={5}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </Field>
        <div className="flex flex-col gap-2">
          <MediaTray items={uploads.items} onRemove={uploads.remove} />
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            hidden
            aria-label="Choose photos"
            onChange={(e) => {
              uploads.add(e.target.files);
              e.target.value = "";
            }}
          />
          <Button
            variant="ghost"
            size="sm"
            className="self-start"
            onClick={() => fileRef.current?.click()}
            disabled={uploads.items.length >= 10}
          >
            Add photos
          </Button>
        </div>
        <Field label="Opens on" hint="At least one day from now.">
          <input
            type="date"
            className={selectCls}
            min={tomorrow()}
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </Field>
        <Field label="Who is it for">
          <select
            className={selectCls}
            value=""
            onChange={(e) => add(e.target.value)}
          >
            <option value="">Add a recipient</option>
            <option value="community:all">Everyone</option>
            <optgroup label="People">
              {members.map((m) => (
                <option key={m.id} value={`user:${m.id}`}>
                  {m.display_name}
                </option>
              ))}
            </optgroup>
            <optgroup label="Groups">
              {groups
                .filter((g) => g.is_member)
                .map((g) => (
                  <option key={g.id} value={`subgroup:${g.id}`}>
                    {g.name}
                  </option>
                ))}
            </optgroup>
            <optgroup label="Household">
              {household.map((h) => (
                <option key={h.id} value={`household:${h.id}`}>
                  {h.name}
                </option>
              ))}
            </optgroup>
          </select>
        </Field>
        {picks.length > 0 && (
          <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
            {picks.map((p) => (
              <li
                key={`${p.kind}:${p.id}`}
                className="glass-item flex items-center gap-1 rounded-full py-1 pr-1 pl-3 text-sm"
              >
                {p.label}
                <button
                  type="button"
                  aria-label={`Remove ${p.label}`}
                  className="focus-visible:outline-accent rounded-full p-1 focus-visible:outline-2"
                  onClick={() => setPicks(picks.filter((x) => x !== p))}
                >
                  <X aria-hidden className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {error && (
          <p role="alert" className="text-danger text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
