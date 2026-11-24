"use client";
/**
 * @file components/admin/sso/ProviderRules.tsx
 * @brief SSO wizard step 3: sign-in rules (JIT create, default role, gates,
 *        email trust, profile sync).
 */
import { useId, useState } from "react";
import { Button, Chip, Input, SettingsRow, Switch } from "@/components/ui";
import { controlClass } from "@/components/ui/Field";
import { cn } from "@/lib/utils";

/** @brief Community roles an SSO user can receive. */
export const COMMUNITY_ROLES = ["viewer", "member", "admin"] as const;

/** @brief Editable rule values. */
export interface RulesValue {
  auto_create_users: boolean;
  default_role: string;
  allowed_domains: string[];
  required_group: string;
  sync_profile: boolean;
  /** Treat the IdP's emails as verified (preset default; see help text). */
  trust_email: boolean;
}

/** @brief Props for ProviderRules. */
export interface ProviderRulesProps {
  value: RulesValue;
  onChange: (next: RulesValue) => void;
}

/**
 * @brief Normalise a typed domain like the backend does (trim, lowercase, no "@").
 * @param raw typed text
 * @return domain or ""
 */
export const normDomain = (raw: string) =>
  raw.trim().replace(/^@+/, "").trim().toLowerCase();

/**
 * @brief Rules editor.
 * @param props see ProviderRulesProps
 * @return rules rows
 */
export function ProviderRules({ value, onChange }: ProviderRulesProps) {
  const [draft, setDraft] = useState("");
  const roleId = useId();
  const set = (patch: Partial<RulesValue>) => onChange({ ...value, ...patch });

  const addDomain = () => {
    const d = normDomain(draft);
    if (d && !value.allowed_domains.includes(d)) {
      set({ allowed_domains: [...value.allowed_domains, d] });
    }
    setDraft("");
  };

  return (
    <div className="flex flex-col">
      <SettingsRow
        label="Create accounts automatically"
        description="Off: only people who already have an account can sign in."
      >
        <Switch
          checked={value.auto_create_users}
          onCheckedChange={(v) => set({ auto_create_users: v })}
          aria-label="Create accounts automatically"
        />
      </SettingsRow>
      <SettingsRow
        label="Default role"
        description="Used when no group mapping grants a role."
      >
        <label htmlFor={roleId} className="sr-only">
          Default role
        </label>
        <select
          id={roleId}
          value={value.default_role}
          onChange={(e) => set({ default_role: e.target.value })}
          className={cn(controlClass, "h-11 rounded-full")}
        >
          {COMMUNITY_ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </SettingsRow>
      <SettingsRow
        label="Allowed email domains"
        description="Empty allows any domain. Only IdP-verified emails count."
      >
        <div className="flex flex-col gap-2">
          {value.allowed_domains.length > 0 && (
            <ul aria-label="Allowed domains" className="flex flex-wrap gap-2">
              {value.allowed_domains.map((d) => (
                <li key={d}>
                  <Chip
                    onRemove={() =>
                      set({
                        allowed_domains: value.allowed_domains.filter(
                          (x) => x !== d,
                        ),
                      })
                    }
                  >
                    {d}
                  </Chip>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Input
                label="Add domain"
                value={draft}
                placeholder="example.com"
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === ",") {
                    e.preventDefault();
                    addDomain();
                  }
                }}
              />
            </div>
            <Button type="button" variant="glass" onClick={addDomain}>
              Add
            </Button>
          </div>
        </div>
      </SettingsRow>
      <SettingsRow
        label="Required group"
        description="Only members of this IdP group may sign in. Empty disables the check."
      >
        <Input
          aria-label="Required group"
          value={value.required_group}
          onChange={(e) => set({ required_group: e.target.value })}
        />
      </SettingsRow>
      <SettingsRow
        label="Treat this provider's emails as verified"
        description="Only turn on if users cannot change their own email at the identity provider — a verified email can sign in to the matching existing account."
      >
        <Switch
          checked={value.trust_email}
          onCheckedChange={(v) => set({ trust_email: v })}
          aria-label="Treat this provider's emails as verified"
        />
      </SettingsRow>
      <SettingsRow
        label="Sync profile"
        description="Update name, avatar and email from the IdP on every sign-in."
      >
        <Switch
          checked={value.sync_profile}
          onCheckedChange={(v) => set({ sync_profile: v })}
          aria-label="Sync profile"
        />
      </SettingsRow>
    </div>
  );
}
