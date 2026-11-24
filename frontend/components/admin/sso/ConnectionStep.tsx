"use client";
/**
 * @file components/admin/sso/ConnectionStep.tsx
 * @brief SSO wizard step 2: discovery/template inputs, client credentials, callback URL.
 */
import { useState } from "react";
import { Copy } from "lucide-react";
import { Button, IconButton, Input } from "@/components/ui";
import type { OAuthPreset } from "@/lib/api/adminOauth";

const PARAM_LABELS: Record<string, string> = {
  host: "Host",
  slug: "Application slug",
  realm: "Realm",
  tenant: "Tenant",
  discovery_url: "Discovery URL",
};

/** @brief Connection field values. */
export interface ConnectionValue {
  display_name: string;
  slug: string;
  client_id: string;
  client_secret: string;
  scopes: string;
  /** Template placeholder values (create with an OIDC preset). */
  params: Record<string, string>;
  /** Full discovery URL (edit mode). */
  discovery_url: string;
}

/** @brief Props for ConnectionStep. */
export interface ConnectionStepProps {
  value: ConnectionValue;
  onChange: (next: ConnectionValue) => void;
  preset: OAuthPreset | undefined;
  editing: boolean;
  /** Effective discovery URL (rendered template or edited URL), if any. */
  discoveryUrl: string | null;
  callbackUrl: string | null;
  errors: Record<string, string>;
  onTest: (url: string) => Promise<unknown>;
}

/**
 * @brief Connection fields; the client secret is write-only.
 * @param props see ConnectionStepProps
 * @return fields
 */
export function ConnectionStep({
  value,
  onChange,
  preset,
  editing,
  discoveryUrl,
  callbackUrl,
  errors,
  onTest,
}: ConnectionStepProps) {
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState<{ ok: boolean; text: string } | null>(
    null,
  );
  const [copied, setCopied] = useState(false);
  const set = (patch: Partial<ConnectionValue>) =>
    onChange({ ...value, ...patch });
  const oidc = (preset?.kind ?? "oidc") === "oidc";
  const templated = !editing && oidc && !!preset && preset.params.length > 0;

  const test = async () => {
    if (!discoveryUrl?.startsWith("https://")) {
      setTestMsg({ ok: false, text: "Discovery URL must use HTTPS" });
      return;
    }
    setTesting(true);
    setTestMsg(null);
    try {
      await onTest(
        discoveryUrl.replace(/\/\.well-known\/openid-configuration$/, ""),
      );
      setTestMsg({ ok: true, text: "Connection OK" });
    } catch {
      setTestMsg({ ok: false, text: "Connection failed" });
    } finally {
      setTesting(false);
    }
  };

  const copy = async () => {
    if (!callbackUrl) return;
    try {
      await navigator.clipboard.writeText(callbackUrl);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Input
        label="Display name"
        value={value.display_name}
        onChange={(e) => set({ display_name: e.target.value })}
        error={errors.display_name}
      />
      <Input
        label="Slug"
        value={value.slug}
        onChange={(e) => set({ slug: e.target.value })}
        hint="Lowercase letters, numbers and dashes; part of the callback URL."
        error={errors.slug}
      />
      {templated &&
        preset.params.map((name) => (
          <Input
            key={name}
            label={PARAM_LABELS[name] ?? name}
            value={value.params[name] ?? preset.defaults[name] ?? ""}
            placeholder={name === "host" ? "auth.example.com" : undefined}
            onChange={(e) =>
              set({ params: { ...value.params, [name]: e.target.value } })
            }
            error={name === "discovery_url" ? errors.discovery : undefined}
          />
        ))}
      {editing && oidc && (
        <Input
          label="Discovery URL"
          type="url"
          value={value.discovery_url}
          onChange={(e) => set({ discovery_url: e.target.value })}
          error={errors.discovery}
        />
      )}
      {oidc && (
        <div className="flex flex-col gap-2">
          {templated && (
            <p className="text-sm break-all text-muted">
              Discovery URL:{" "}
              <span className="text-ink">
                {discoveryUrl ?? "fill in the fields above"}
              </span>
            </p>
          )}
          {templated &&
            errors.discovery &&
            !preset.params.includes("discovery_url") && (
              <p className="text-sm text-destructive">{errors.discovery}</p>
            )}
          <div className="flex items-center gap-3">
            <Button
              type="button"
              size="sm"
              variant="glass"
              onClick={test}
              loading={testing}
            >
              Test connection
            </Button>
            {testMsg && (
              <span
                role="status"
                className={testMsg.ok ? "text-sm" : "text-sm text-destructive"}
              >
                {testMsg.text}
              </span>
            )}
          </div>
        </div>
      )}
      <Input
        label="Client ID"
        value={value.client_id}
        onChange={(e) => set({ client_id: e.target.value })}
        error={errors.client_id}
      />
      <Input
        label="Client secret"
        type="password"
        autoComplete="new-password"
        value={value.client_secret}
        placeholder={editing ? "Leave blank to keep current" : undefined}
        onChange={(e) => set({ client_secret: e.target.value })}
        error={errors.client_secret}
      />
      <Input
        label="Scopes"
        value={value.scopes}
        onChange={(e) => set({ scopes: e.target.value })}
      />
      <div className="flex flex-col gap-1.5">
        <p className="text-sm font-medium" id="sso-callback-label">
          Callback URL
        </p>
        <div className="flex items-center gap-2">
          <code
            aria-labelledby="sso-callback-label"
            className="min-w-0 flex-1 rounded-2xl bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] px-3 py-2 text-xs break-all"
          >
            {callbackUrl ?? "Enter a slug"}
          </code>
          <IconButton
            variant="glass"
            aria-label="Copy callback URL"
            onClick={copy}
            disabled={!callbackUrl}
          >
            <Copy className="size-4" aria-hidden="true" />
          </IconButton>
        </div>
        <p className="text-sm text-muted" role="status">
          {copied
            ? "Copied."
            : "Register this redirect URI at your identity provider."}
        </p>
      </div>
    </div>
  );
}
