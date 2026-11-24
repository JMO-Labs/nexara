"use client";
/**
 * @file components/admin/SsoProviderForm.tsx
 * @brief SSO provider wizard: preset -> connection -> rules -> mappings -> test.
 *
 * Steps are announced by moving focus to the step heading. Edit mode starts
 * at Connection and never prefills the client secret (blank keeps it).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";
import { useCallbackTemplate, useOauthPresets } from "@/hooks/useAdminOauth";
import { useSubgroupList } from "@/hooks/useSubgroups";
import type {
  OAuthProviderCreate,
  OAuthProviderResponse,
} from "@/lib/api/adminOauth";
import { PresetPicker, renderDiscoveryUrl } from "./sso/PresetPicker";
import { ConnectionStep, type ConnectionValue } from "./sso/ConnectionStep";
import { ProviderRules, type RulesValue } from "./sso/ProviderRules";
import {
  GroupMappingEditor,
  mappingToRows,
  rowsToMapping,
  type MappingRow,
} from "./sso/GroupMappingEditor";
import { TestLoginPanel } from "./sso/TestLoginPanel";

const STEPS = ["Preset", "Connection", "Rules", "Mappings", "Test"] as const;
const DEFAULT_SCOPES = "openid profile email";
const SLUG_RE = /^[a-z0-9][a-z0-9-]*$/;
const WELL_KNOWN = "/.well-known/openid-configuration";

/** @brief Props for SsoProviderForm. */
export interface SsoProviderFormProps {
  provider?: OAuthProviderResponse | null;
  pending: boolean;
  onCancel: () => void;
  onSubmit: (values: OAuthProviderCreate, secretChanged: boolean) => void;
  onTest: (url: string) => Promise<unknown>;
  /** Server rejected the slug (409 sso_slug_taken): shown on the slug field. */
  slugError?: string | null;
}

const initialDiscovery = (p?: OAuthProviderResponse | null) =>
  p?.discovery_url ??
  (p?.issuer ? `${p.issuer.replace(/\/$/, "")}${WELL_KNOWN}` : "");

/**
 * @brief Provider wizard.
 * @param props see SsoProviderFormProps
 * @return form element
 */
export function SsoProviderForm({
  provider,
  pending,
  onCancel,
  onSubmit,
  onTest,
  slugError,
}: SsoProviderFormProps) {
  const editing = !!provider;
  const { data: presets = [] } = useOauthPresets();
  const { data: cbTemplate } = useCallbackTemplate();
  const { data: subgroups = [] } = useSubgroupList();
  const [step, setStep] = useState(editing ? 1 : 0);
  const [presetKey, setPresetKey] = useState<string | null>(
    provider ? (provider.preset ?? "custom") : null,
  );
  const [conn, setConn] = useState<ConnectionValue>({
    display_name: provider?.display_name ?? "",
    slug: provider?.slug ?? "",
    client_id: provider?.client_id ?? "",
    client_secret: "",
    scopes: provider?.scopes ?? DEFAULT_SCOPES,
    params: {},
    discovery_url: initialDiscovery(provider),
  });
  const [rules, setRules] = useState<RulesValue>({
    auto_create_users: provider?.auto_create_users ?? true,
    default_role: provider?.default_role ?? "member",
    allowed_domains: provider?.allowed_domains ?? [],
    required_group: provider?.required_group ?? "",
    sync_profile: provider?.sync_profile ?? true,
    trust_email: provider?.trust_email ?? false,
  });
  const [rows, setRows] = useState<MappingRow[]>(() =>
    mappingToRows(provider?.claim_mapping?.group_mapping),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const heading = useRef<HTMLHeadingElement>(null);
  const mounted = useRef(false);

  useEffect(() => {
    if (mounted.current) heading.current?.focus();
    mounted.current = true;
  }, [step]);

  // A new server slug error (409) jumps back to Connection (state adjusted
  // during render, not in an effect).
  const [seenSlugError, setSeenSlugError] = useState<string | null>(null);
  if (slugError && slugError !== seenSlugError) {
    setSeenSlugError(slugError);
    setErrors((e) => ({ ...e, slug: slugError }));
    setStep(1);
  }

  const preset = presets.find((p) => p.key === presetKey);
  const kind = preset?.kind ?? provider?.provider_type ?? "oidc";
  const discoveryUrl = useMemo(() => {
    if (kind !== "oidc") return null;
    if (editing) return conn.discovery_url.trim() || null;
    if (!preset) return null;
    return renderDiscoveryUrl(preset.discovery_url, {
      ...preset.defaults,
      ...conn.params,
    });
  }, [kind, editing, preset, conn.discovery_url, conn.params]);
  const slug = conn.slug.trim();
  const callbackUrl =
    provider?.slug === slug && provider.callback_url
      ? provider.callback_url
      : slug && cbTemplate
        ? cbTemplate.template.replace("{slug}", slug)
        : null;

  const choosePreset = (key: string) => {
    const p = presets.find((x) => x.key === key);
    setPresetKey(key);
    if (!p || editing) return;
    setConn((c) => ({
      ...c,
      scopes: p.scopes,
      display_name: c.display_name || p.label,
      slug: c.slug || p.key,
    }));
    setRules((r) => ({ ...r, trust_email: p.trust_email }));
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (!conn.display_name.trim()) e.display_name = "Required";
    if (!SLUG_RE.test(slug)) e.slug = "Use lowercase letters, numbers, dashes";
    if (!conn.client_id.trim()) e.client_id = "Required";
    if (!editing && !conn.client_secret) e.client_secret = "Required";
    if (kind === "oidc" && !discoveryUrl?.startsWith("https://")) {
      e.discovery = "Discovery URL must use HTTPS";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const go = (to: number) => {
    if (step === 1 && to > 1 && !validate()) return;
    setStep(to);
  };

  const submit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!presetKey) return setStep(0);
    if (!validate()) return setStep(1);
    const base = {
      ...(provider?.claim_mapping ?? preset?.claim_mapping ?? {}),
    };
    delete base.group_mapping;
    const values: OAuthProviderCreate = {
      slug,
      display_name: conn.display_name.trim(),
      provider_type: kind,
      client_id: conn.client_id.trim(),
      client_secret: conn.client_secret,
      scopes: conn.scopes.trim() || DEFAULT_SCOPES,
      claim_mapping: { ...base, group_mapping: rowsToMapping(rows) },
      ...rules,
      required_group: rules.required_group.trim() || null,
    };
    if (!editing && preset) values.preset = preset.key;
    if (
      discoveryUrl &&
      (!editing || discoveryUrl !== initialDiscovery(provider))
    ) {
      values.discovery_url = discoveryUrl;
    }
    if (!editing && preset?.kind === "oauth2") {
      values.authorization_endpoint =
        preset.authorization_endpoint ?? undefined;
      values.token_endpoint = preset.token_endpoint ?? undefined;
      values.userinfo_endpoint = preset.userinfo_endpoint ?? undefined;
    }
    onSubmit(values, !!conn.client_secret);
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-5">
      <nav aria-label="Setup steps">
        <ol className="flex flex-wrap gap-1">
          {STEPS.map((label, i) => (
            <li key={label}>
              <button
                type="button"
                onClick={() => go(i)}
                disabled={i === 0 && editing}
                aria-current={i === step ? "step" : undefined}
                className={cn(
                  "min-h-11 rounded-full px-3 text-sm disabled:opacity-50",
                  i === step
                    ? "bg-[var(--nx-blue)]/15 font-semibold"
                    : "text-muted",
                )}
              >
                {i + 1}. {label}
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <h3 ref={heading} tabIndex={-1} className="font-semibold outline-none">
        Step {step + 1} of {STEPS.length}: {STEPS[step]}
      </h3>

      {step === 0 && (
        <PresetPicker
          presets={presets}
          value={presetKey}
          onChange={choosePreset}
        />
      )}
      {step === 1 && (
        <ConnectionStep
          value={conn}
          onChange={setConn}
          preset={preset}
          editing={editing}
          discoveryUrl={discoveryUrl}
          callbackUrl={callbackUrl}
          errors={errors}
          onTest={onTest}
        />
      )}
      {step === 2 && <ProviderRules value={rules} onChange={setRules} />}
      {step === 3 && (
        <GroupMappingEditor rows={rows} groups={subgroups} onChange={setRows} />
      )}
      {step === 4 && <TestLoginPanel providerId={provider?.id ?? null} />}

      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        {step > (editing ? 1 : 0) && (
          <Button type="button" variant="glass" onClick={() => go(step - 1)}>
            Back
          </Button>
        )}
        {step < STEPS.length - 1 && (
          <Button
            type="button"
            variant="glass"
            onClick={() => go(step + 1)}
            disabled={step === 0 && !presetKey}
          >
            Next
          </Button>
        )}
        <Button type="submit" loading={pending} disabled={!presetKey}>
          {editing ? "Save changes" : "Create provider"}
        </Button>
      </div>
    </form>
  );
}
