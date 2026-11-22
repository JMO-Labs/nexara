"use client";
/**
 * @file components/household/HouseholdEditor.tsx
 * @brief Add/edit a household member or pet in a modal. Pet-only fields
 *        (species, breed, gotcha day, likes, care card) show for pets.
 */
import * as React from "react";
import { Button, Checkbox, Input, Modal, Textarea } from "@/components/ui";
import { CoverPicker } from "@/components/media/CoverPicker";
import { useSaveHousehold } from "@/hooks/useHousehold";
import type {
  HouseholdInput,
  HouseholdKind,
  HouseholdMember,
} from "@/lib/api/household";
import { LEVEL_LABEL, type ProfileLevel } from "@/lib/profile";
import { useConfirmDialog } from "@/stores/confirmDialog";

const split = (s: string) =>
  s
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium">{label}</span>
      {children}
    </label>
  );
}

function LevelSelect({
  value,
  onChange,
  label,
}: {
  value: ProfileLevel;
  onChange: (v: ProfileLevel) => void;
  label: string;
}) {
  return (
    <Row label={label}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as ProfileLevel)}
        className="glass-item h-10 rounded-full px-3 text-sm focus-visible:outline-2 focus-visible:outline-accent"
      >
        {(Object.keys(LEVEL_LABEL) as ProfileLevel[]).map((l) => (
          <option key={l} value={l}>
            {LEVEL_LABEL[l]}
          </option>
        ))}
      </select>
    </Row>
  );
}

/**
 * @brief Household member form.
 * @param member existing member, or null to add
 * @param kind kind for a new member
 * @param onClose close handler
 * @return modal
 */
export function HouseholdEditor({
  member,
  kind,
  onClose,
}: {
  member: HouseholdMember | null;
  kind: HouseholdKind;
  onClose: () => void;
}) {
  const { create, update, remove } = useSaveHousehold();
  const confirm = useConfirmDialog((s) => s.confirm);
  const m = member;
  const isPet = (m?.kind ?? kind) === "pet";
  const [f, setF] = React.useState({
    name: m?.name ?? "",
    relation: m?.relation ?? "",
    birthday: m?.birthday && !m.birthday.startsWith("--") ? m.birthday : "",
    show_birth_year: m?.show_birth_year ?? false,
    photo_media_id: m?.photo_media_id ?? null,
    visibility: m?.visibility ?? ("groups" as ProfileLevel),
    bio: m?.bio ?? "",
    species: m?.species ?? "",
    breed: m?.breed ?? "",
    gotcha_day: m?.gotcha_day ?? "",
    likes: (m?.likes ?? []).join(", "),
    dislikes: (m?.dislikes ?? []).join(", "),
    care_card: m?.care_card ?? "",
    care_visibility: m?.care_visibility ?? ("private" as ProfileLevel),
  });
  const [error, setError] = React.useState<string | null>(null);
  const set = (p: Partial<typeof f>) => setF((o) => ({ ...o, ...p }));
  const pending = create.isPending || update.isPending;

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!f.name.trim()) return setError("Add a name.");
    const body: HouseholdInput = {
      name: f.name.trim(),
      relation: f.relation,
      birthday: f.birthday || null,
      show_birth_year: f.show_birth_year,
      photo_media_id: f.photo_media_id,
      visibility: f.visibility,
      bio: f.bio,
      ...(isPet && {
        species: f.species,
        breed: f.breed,
        gotcha_day: f.gotcha_day || null,
        likes: split(f.likes),
        dislikes: split(f.dislikes),
        care_card: f.care_card,
        care_visibility: f.care_visibility,
      }),
    };
    const opts = {
      onSuccess: onClose,
      onError: (err: unknown) =>
        setError(err instanceof Error ? err.message : "Couldn't save."),
    };
    if (m) update.mutate({ id: m.id, body }, opts);
    else create.mutate({ ...body, kind }, opts);
  };

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title={m ? `Edit ${m.name}` : isPet ? "Add a pet" : "Add a family member"}
      description="Family members and pets don't need an account. You manage their details."
    >
      <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
        <Row label="Name">
          <Input
            value={f.name}
            maxLength={80}
            required
            onChange={(e) => set({ name: e.target.value })}
          />
        </Row>
        <Row label={isPet ? "Whose pet" : "Relation"}>
          <Input
            value={f.relation}
            maxLength={60}
            placeholder={isPet ? "Family dog" : "Daughter, grandpa…"}
            onChange={(e) => set({ relation: e.target.value })}
          />
        </Row>
        {isPet && (
          <>
            <Row label="Species">
              <Input
                value={f.species}
                maxLength={40}
                placeholder="Dog, cat, gecko…"
                onChange={(e) => set({ species: e.target.value })}
              />
            </Row>
            <Row label="Breed">
              <Input
                value={f.breed}
                maxLength={60}
                onChange={(e) => set({ breed: e.target.value })}
              />
            </Row>
          </>
        )}
        <Row label="Birthday">
          <Input
            type="date"
            value={f.birthday}
            onChange={(e) => set({ birthday: e.target.value })}
          />
        </Row>
        {isPet ? (
          <Row label="Gotcha day">
            <Input
              type="date"
              value={f.gotcha_day}
              onChange={(e) => set({ gotcha_day: e.target.value })}
            />
          </Row>
        ) : (
          <span />
        )}
        <label className="flex items-center gap-2 text-sm sm:col-span-2">
          <Checkbox
            checked={f.show_birth_year}
            onCheckedChange={(v) => set({ show_birth_year: v === true })}
          />
          Show birth year to others
        </label>
        <div className="sm:col-span-2">
          <Row label="Photo">
            <CoverPicker
              label="Photo"
              mediaId={f.photo_media_id}
              onChange={(id) => set({ photo_media_id: id })}
            />
          </Row>
        </div>
        <div className="sm:col-span-2">
          <Row label={isPet ? "About" : "Bio"}>
            <Textarea
              rows={2}
              maxLength={1000}
              value={f.bio}
              onChange={(e) => set({ bio: e.target.value })}
            />
          </Row>
        </div>
        {isPet && (
          <>
            <Row label="Likes">
              <Input
                value={f.likes}
                placeholder="Walks, tennis balls"
                onChange={(e) => set({ likes: e.target.value })}
              />
            </Row>
            <Row label="Dislikes">
              <Input
                value={f.dislikes}
                placeholder="Vacuum, baths"
                onChange={(e) => set({ dislikes: e.target.value })}
              />
            </Row>
            <div className="sm:col-span-2">
              <Row label="Care card">
                <Textarea
                  rows={3}
                  maxLength={4000}
                  placeholder="Food, meds, vet phone, walk times"
                  value={f.care_card}
                  onChange={(e) => set({ care_card: e.target.value })}
                />
              </Row>
            </div>
            <LevelSelect
              label="Who sees the care card"
              value={f.care_visibility}
              onChange={(v) => set({ care_visibility: v })}
            />
          </>
        )}
        <LevelSelect
          label={`Who sees ${isPet ? "this pet" : "them"}`}
          value={f.visibility}
          onChange={(v) => set({ visibility: v })}
        />
        {error && (
          <p role="alert" className="text-sm text-destructive sm:col-span-2">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2 sm:col-span-2">
          {m && (
            <Button
              type="button"
              variant="ghost"
              className="mr-auto text-destructive"
              onClick={async () => {
                const ok = await confirm({
                  title: `Remove ${m.name}?`,
                  message: "Their photo tags are removed too.",
                  confirmLabel: "Remove",
                  tone: "danger",
                });
                if (ok) remove.mutate(m.id, { onSuccess: onClose });
              }}
            >
              Remove
            </Button>
          )}
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending} disabled={pending}>
            {m ? "Save" : "Add"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
