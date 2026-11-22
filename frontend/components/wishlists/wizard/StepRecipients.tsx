"use client";
/**
 * @file components/wishlists/wizard/StepRecipients.tsx
 * @brief Wizard step 2: who the list is for. Any mix of members, household
 *        members/pets, groups you're in and typed names, or everyone.
 */
import * as React from "react";
import { Globe, PawPrint, Plus, User, Users, X } from "lucide-react";
import { Button, IconButton, Input } from "@/components/ui";
import { useMembersList } from "@/hooks/useMembersList";
import { useVisibleHousehold } from "@/hooks/useHousehold";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useSession } from "@/stores/session";
import type { Draft, PickedRecipient } from "./draft";

const ICON = {
  user: User,
  household: PawPrint,
  subgroup: Users,
  name: User,
  everyone: Globe,
};

/**
 * @brief Recipient picker.
 * @param d draft
 * @param set patch the draft
 * @return step body
 */
export function StepRecipients({
  d,
  set,
}: {
  d: Draft;
  set: (p: Partial<Draft>) => void;
}) {
  const me = useSession((s) => s.user);
  const { data: members = [] } = useMembersList();
  const { data: household = [] } = useVisibleHousehold();
  const { data: groups = [] } = useSubgroupList();
  const [q, setQ] = React.useState("");
  const everyone = d.recipients.some((r) => r.kind === "everyone");

  const key = (r: PickedRecipient) => `${r.kind}:${r.ref_id ?? r.name}`;
  const add = (r: PickedRecipient) => {
    if (r.kind === "everyone") return set({ recipients: [r] });
    const rest = d.recipients.filter(
      (x) => x.kind !== "everyone" && key(x) !== key(r),
    );
    set({ recipients: [...rest, r] });
    setQ("");
  };
  const remove = (r: PickedRecipient) =>
    set({ recipients: d.recipients.filter((x) => key(x) !== key(r)) });

  const n = q.trim().toLowerCase();
  const matches: PickedRecipient[] = n
    ? [
        ...members
          .filter((u) =>
            `${u.display_name} ${u.username}`.toLowerCase().includes(n),
          )
          .slice(0, 5)
          .map((u) => ({
            kind: "user" as const,
            ref_id: u.id,
            label: u.display_name,
          })),
        ...household
          .filter((h) => h.name.toLowerCase().includes(n))
          .slice(0, 4)
          .map((h) => ({
            kind: "household" as const,
            ref_id: h.id,
            label: h.name,
          })),
        ...groups
          .filter((g) => g.is_member && g.name.toLowerCase().includes(n))
          .slice(0, 3)
          .map((g) => ({
            kind: "subgroup" as const,
            ref_id: g.id,
            label: g.name,
          })),
      ]
    : [];

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        One person, a few, a whole group or everyone. People named here can add
        wishes.
      </p>
      <div className="flex flex-wrap gap-2">
        {me && (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => add({ kind: "user", ref_id: me.id, label: "Me" })}
          >
            <User className="size-4" aria-hidden /> Me
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => add({ kind: "everyone", label: "Everyone" })}
        >
          <Globe className="size-4" aria-hidden /> Everyone
        </Button>
      </div>
      <ul aria-label="Recipients" className="flex flex-wrap gap-2">
        {d.recipients.map((r) => {
          const Icon = ICON[r.kind];
          return (
            <li
              key={key(r)}
              className="glass-item inline-flex items-center gap-1.5 rounded-full py-1 pr-1 pl-3 text-sm"
            >
              <Icon className="size-3.5" aria-hidden />
              {r.label}
              <IconButton
                variant="ghost"
                size="sm"
                aria-label={`Remove ${r.label}`}
                onClick={() => remove(r)}
              >
                <X className="size-3.5" aria-hidden />
              </IconButton>
            </li>
          );
        })}
      </ul>
      {!everyone && (
        <div className="flex flex-col gap-2">
          <Input
            aria-label="Find a person, pet or group, or type a name"
            placeholder="Find a person, pet or group, or type any name"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && q.trim()) {
                e.preventDefault();
                add(
                  matches[0] ?? {
                    kind: "name",
                    name: q.trim(),
                    label: q.trim(),
                  },
                );
              }
            }}
          />
          {q.trim() && (
            <ul
              className="glass-item flex flex-col rounded-[20px] p-1.5"
              aria-label="Suggestions"
            >
              {matches.map((m) => {
                const Icon = ICON[m.kind];
                return (
                  <li key={key(m)}>
                    <button
                      type="button"
                      onClick={() => add(m)}
                      className="flex w-full items-center gap-2 rounded-full px-3 py-2 text-left text-sm hover:bg-[color-mix(in_srgb,var(--nx-ink)_7%,transparent)] focus-visible:outline-2 focus-visible:outline-accent"
                    >
                      <Icon className="size-4" aria-hidden /> {m.label}
                      <span className="ml-auto text-xs text-muted">
                        {m.kind === "household"
                          ? "Household"
                          : m.kind === "subgroup"
                            ? "Group"
                            : "Member"}
                      </span>
                    </button>
                  </li>
                );
              })}
              <li>
                <button
                  type="button"
                  onClick={() =>
                    add({ kind: "name", name: q.trim(), label: q.trim() })
                  }
                  className="flex w-full items-center gap-2 rounded-full px-3 py-2 text-left text-sm hover:bg-[color-mix(in_srgb,var(--nx-ink)_7%,transparent)] focus-visible:outline-2 focus-visible:outline-accent"
                >
                  <Plus className="size-4" aria-hidden /> Add &ldquo;{q.trim()}
                  &rdquo; as a name
                </button>
              </li>
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
