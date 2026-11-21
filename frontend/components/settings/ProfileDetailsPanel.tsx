"use client";
/**
 * @file components/settings/ProfileDetailsPanel.tsx
 * @brief Settings "Contact & about": banner, birthday, phone, contact email,
 *        address, links, skills, availability, dietary, emergency contact.
 *        Each field has its own privacy picker (saved instantly); values
 *        save together with "Save details".
 */
import * as React from "react";
import Link from "next/link";
import { Plus, X } from "lucide-react";
import {
  Button,
  IconButton,
  Input,
  SettingsRow,
  Textarea,
} from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { CoverPicker } from "@/components/media/CoverPicker";
import { useMyProfile, useUpdateProfile } from "@/hooks/useSettings";
import type { ProfileUpdate } from "@/lib/api/settings";
import { VisibilitySelect } from "./VisibilitySelect";

type LinkRow = { label: string; url: string };
interface Draft {
  birthday: string;
  phone: string;
  contact_email: string;
  address: string;
  links: LinkRow[];
  skills: string;
  availability: string;
  dietary: string;
  ec_name: string;
  ec_phone: string;
  ec_relation: string;
}

const URL_RE = /^https?:\/\/\S+$/i;

/** @brief Field row: control plus its privacy picker. */
function Field({
  label,
  description,
  field,
  children,
}: {
  label: string;
  description?: string;
  field?: string;
  children: React.ReactNode;
}) {
  return (
    <SettingsRow label={label} description={description}>
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">{children}</div>
        {field && (
          <VisibilitySelect field={field} label={label.toLowerCase()} />
        )}
      </div>
    </SettingsRow>
  );
}

/**
 * @brief Contact & about panel.
 * @return panel
 */
export function ProfileDetailsPanel() {
  const { data: me } = useMyProfile();
  const { mutate, isPending } = useUpdateProfile();
  const [draft, setDraft] = React.useState<Draft | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const base: Draft | null = React.useMemo(
    () =>
      me
        ? {
            birthday: me.birthday ?? "",
            phone: me.phone ?? "",
            // Pre-filled from the sign-in email; editable, private by default.
            contact_email: me.contact_email ?? me.email ?? "",
            address: me.address ?? "",
            links: me.links ?? [],
            skills: (me.skills ?? []).join(", "),
            availability: me.availability ?? "",
            dietary: me.dietary ?? "",
            ec_name: me.emergency_contact?.name ?? "",
            ec_phone: me.emergency_contact?.phone ?? "",
            ec_relation: me.emergency_contact?.relation ?? "",
          }
        : null,
    [me],
  );
  const d = draft ?? base;
  if (!me || !d) return null;
  const set = (p: Partial<Draft>) => setDraft({ ...d, ...p });
  const setLink = (i: number, p: Partial<LinkRow>) =>
    set({ links: d.links.map((l, j) => (j === i ? { ...l, ...p } : l)) });

  const save = () => {
    const links = d.links
      .map((l) => ({ label: l.label.trim(), url: l.url.trim() }))
      .filter((l) => l.url);
    if (links.some((l) => !URL_RE.test(l.url))) {
      setError("Links must start with http:// or https://");
      return;
    }
    const ec = [d.ec_name, d.ec_phone].map((v) => v.trim());
    if (ec.some(Boolean) && !ec.every(Boolean)) {
      setError("Emergency contact needs both a name and a phone number.");
      return;
    }
    setError(null);
    const body: ProfileUpdate = {
      birthday: d.birthday || null,
      phone: d.phone.trim(),
      contact_email: d.contact_email.trim(),
      address: d.address.trim(),
      links,
      skills: d.skills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      availability: d.availability.trim(),
      dietary: d.dietary.trim(),
      emergency_contact: ec[0]
        ? { name: ec[0], phone: ec[1], relation: d.ec_relation.trim() }
        : null,
    };
    mutate(body, { onSuccess: () => setDraft(null) });
  };

  return (
    <Panel title="Contact & about">
      <p className="mb-2 text-sm text-muted">
        Choose who sees each detail: only you, people in your invite-only
        groups, or everyone in the community.
      </p>
      <SettingsRow
        label="Profile banner"
        description="Shown across the top of your profile."
      >
        <CoverPicker
          label="Banner image"
          mediaId={me.banner_media_id ?? null}
          onChange={(id) => mutate({ banner_media_id: id })}
        />
      </SettingsRow>
      <SettingsRow
        label="Birthday"
        description="Who sees it is set in the Privacy tab."
      >
        <div className="flex items-center gap-3">
          <Input
            type="date"
            aria-label="Birthday"
            value={d.birthday}
            onChange={(e) => set({ birthday: e.target.value })}
          />
          <Link href="?tab=privacy" className="text-xs text-muted underline">
            Birthday privacy
          </Link>
        </div>
      </SettingsRow>
      <Field label="Phone" field="phone">
        <Input
          type="tel"
          aria-label="Phone"
          autoComplete="tel"
          value={d.phone}
          maxLength={40}
          onChange={(e) => set({ phone: e.target.value })}
        />
      </Field>
      <Field
        label="Contact email"
        description="Can differ from the email you sign in with."
        field="contact_email"
      >
        <Input
          type="email"
          aria-label="Contact email"
          value={d.contact_email}
          onChange={(e) => set({ contact_email: e.target.value })}
        />
      </Field>
      <Field label="Address" field="address">
        <Textarea
          aria-label="Address"
          rows={2}
          maxLength={300}
          autoComplete="street-address"
          value={d.address}
          onChange={(e) => set({ address: e.target.value })}
        />
      </Field>
      <Field
        label="Links"
        description="Instagram, Facebook, TikTok and others show their icon."
        field="links"
      >
        <div className="flex flex-col gap-2">
          {d.links.map((l, i) => (
            <div key={i} className="flex gap-2">
              <Input
                aria-label={`Link ${i + 1} label`}
                placeholder="Label (optional)"
                value={l.label}
                maxLength={40}
                onChange={(e) => setLink(i, { label: e.target.value })}
                className="w-36"
              />
              <Input
                type="url"
                aria-label={`Link ${i + 1} URL`}
                placeholder="https://instagram.com/you"
                value={l.url}
                onChange={(e) => setLink(i, { url: e.target.value })}
              />
              <IconButton
                aria-label={`Remove link ${i + 1}`}
                variant="ghost"
                size="sm"
                onClick={() =>
                  set({ links: d.links.filter((_, j) => j !== i) })
                }
              >
                <X className="size-4" aria-hidden />
              </IconButton>
            </div>
          ))}
          {d.links.length < 12 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="self-start"
              onClick={() =>
                set({ links: [...d.links, { label: "", url: "" }] })
              }
            >
              <Plus className="size-4" aria-hidden /> Add link
            </Button>
          )}
        </div>
      </Field>
      <Field
        label="Can help with"
        description="Comma separated, e.g. plumbing, tutoring, rides."
        field="skills"
      >
        <Input
          aria-label="Can help with"
          value={d.skills}
          onChange={(e) => set({ skills: e.target.value })}
        />
      </Field>
      <Field label="Usually available" field="availability">
        <Input
          aria-label="Usually available"
          placeholder="Weekday evenings, Sunday mornings"
          maxLength={200}
          value={d.availability}
          onChange={(e) => set({ availability: e.target.value })}
        />
      </Field>
      <Field
        label="Dietary needs"
        description="Handy for potlucks and events."
        field="dietary"
      >
        <Input
          aria-label="Dietary needs"
          placeholder="Vegetarian, nut allergy"
          maxLength={300}
          value={d.dietary}
          onChange={(e) => set({ dietary: e.target.value })}
        />
      </Field>
      <Field label="Emergency contact" field="emergency_contact">
        <div className="grid gap-2 sm:grid-cols-3">
          <Input
            aria-label="Emergency contact name"
            placeholder="Name"
            value={d.ec_name}
            onChange={(e) => set({ ec_name: e.target.value })}
          />
          <Input
            type="tel"
            aria-label="Emergency contact phone"
            placeholder="Phone"
            value={d.ec_phone}
            onChange={(e) => set({ ec_phone: e.target.value })}
          />
          <Input
            aria-label="Emergency contact relation"
            placeholder="Relation"
            value={d.ec_relation}
            onChange={(e) => set({ ec_relation: e.target.value })}
          />
        </div>
      </Field>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="mt-4 flex items-center gap-3">
        <Button
          onClick={save}
          loading={isPending}
          disabled={isPending || !draft}
        >
          Save details
        </Button>
        {draft && (
          <Button variant="ghost" onClick={() => setDraft(null)}>
            Discard
          </Button>
        )}
      </div>
    </Panel>
  );
}
