"use client";
/**
 * @file components/feed/CelebrateComposer.tsx
 * @brief "Celebrate" modal: pick a person or pet, the occasion, add a note.
 *        Creates a community post with a celebration banner.
 */
import * as React from "react";
import { Button, Modal, Textarea } from "@/components/ui";
import { Segmented } from "@/components/ui/page";
import { selectCls } from "@/components/wishlists/wizard/fields";
import { useMembersList } from "@/hooks/useMembersList";
import { useVisibleHousehold } from "@/hooks/useHousehold";
import { useCreatePost } from "@/hooks/usePosts";
import type { CelebrateIn, CelebrateOccasion } from "@/lib/api/posts";

const PLACEHOLDER: Record<CelebrateOccasion, string> = {
  birthday: "Wishing you the happiest birthday!",
  gotcha_day: "Another year of zoomies and naps. Happy gotcha day!",
  milestone: "So proud of you!",
};

/** @brief Celebrate modal; ``initial`` preselects a person/pet and occasion. */
export function CelebrateComposer({
  open,
  onClose,
  initial,
}: {
  open: boolean;
  onClose: () => void;
  initial?: Partial<CelebrateIn>;
}) {
  const { data: members = [] } = useMembersList();
  const { data: household = [] } = useVisibleHousehold();
  const create = useCreatePost();
  const [who, setWho] = React.useState(
    initial?.subject_id ? `${initial.subject_type}:${initial.subject_id}` : "",
  );
  const [occasion, setOccasion] = React.useState<CelebrateOccasion>(
    initial?.occasion ?? "birthday",
  );
  const [note, setNote] = React.useState("");
  const [kind, id] = who.split(":") as ["user" | "household" | "", string];
  const pet = household.find((m) => m.id === id)?.kind === "pet";
  const occ = occasion === "gotcha_day" && !pet ? "birthday" : occasion;
  const submit = () =>
    kind &&
    create.mutate(
      {
        content: note.trim(),
        celebrate: { subject_type: kind, subject_id: id, occasion: occ },
      },
      { onSuccess: onClose },
    );
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Celebrate someone"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!kind || create.isPending}>
            Post celebration
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm font-semibold">
          Who
          <select
            className={selectCls}
            value={who}
            onChange={(e) => setWho(e.target.value)}
          >
            <option value="">Choose a person or pet</option>
            <optgroup label="People">
              {members.map((m) => (
                <option key={m.id} value={`user:${m.id}`}>
                  {m.display_name}
                </option>
              ))}
            </optgroup>
            {household.length > 0 && (
              <optgroup label="Family and pets">
                {household.map((m) => (
                  <option key={m.id} value={`household:${m.id}`}>
                    {m.name}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </label>
        <Segmented
          label="Occasion"
          value={occ}
          onChange={setOccasion}
          options={[
            { value: "birthday", label: "Birthday" },
            ...(pet
              ? [{ value: "gotcha_day" as const, label: "Gotcha day" }]
              : []),
            { value: "milestone", label: "Milestone" },
          ]}
        />
        <label className="flex flex-col gap-1.5 text-sm font-semibold">
          Message
          <Textarea
            rows={3}
            maxLength={2000}
            placeholder={PLACEHOLDER[occ]}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
      </div>
    </Modal>
  );
}
