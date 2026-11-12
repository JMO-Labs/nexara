"use client";
/**
 * @file components/admin/SsoProviderForm.tsx
 * @brief Add/edit OIDC provider form with HTTPS validation and test connection.
 */
import { useState } from "react";
import { Button, Checkbox, Input, Textarea } from "@/components/ui";
import type {
  OAuthProviderCreate,
  OAuthProviderResponse,
} from "@/lib/api/adminOauth";

const DEFAULT_SCOPES = "openid profile email";

/** @brief Props for SsoProviderForm. */
export interface SsoProviderFormProps {
  provider?: OAuthProviderResponse | null;
  pending: boolean;
  onCancel: () => void;
  onSubmit: (values: OAuthProviderCreate, secretChanged: boolean) => void;
  onTest: (url: string) => Promise<unknown>;
}

/**
 * @brief Provider form; edit mode never prefills the client secret.
 * @param props see SsoProviderFormProps
 * @return form element
 */
export function SsoProviderForm({
  provider,
  pending,
  onCancel,
  onSubmit,
  onTest,
}: SsoProviderFormProps) {
  const editing = !!provider;
  const [slug, setSlug] = useState(provider?.slug ?? "");
  const [url, setUrl] = useState(provider?.issuer ?? "");
  const [clientId, setClientId] = useState(provider?.client_id ?? "");
  const [secret, setSecret] = useState("");
  const [changeSecret, setChangeSecret] = useState(false);
  const [scopes, setScopes] = useState(provider?.scopes ?? DEFAULT_SCOPES);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState<{ ok: boolean; text: string } | null>(
    null,
  );
  const showSecret = !editing || changeSecret;

  const validate = () => {
    const e: Record<string, string> = {};
    if (!slug.trim()) e.slug = "Required";
    if (!url.startsWith("https://")) e.url = "Discovery URL must use HTTPS";
    if (!clientId.trim()) e.clientId = "Required";
    if (showSecret && !secret) e.secret = "Required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!validate()) return;
    onSubmit(
      {
        slug: slug.trim(),
        display_name: provider?.display_name ?? slug.trim(),
        provider_type: "oidc",
        client_id: clientId.trim(),
        client_secret: showSecret ? secret : "",
        issuer: url,
        scopes: scopes.trim() || DEFAULT_SCOPES,
      },
      showSecret,
    );
  };

  const test = async () => {
    if (!url.startsWith("https://")) {
      setErrors((p) => ({ ...p, url: "Discovery URL must use HTTPS" }));
      return;
    }
    setTesting(true);
    setTestMsg(null);
    try {
      await onTest(url);
      setTestMsg({ ok: true, text: "Connection OK" });
    } catch {
      setTestMsg({ ok: false, text: "Connection failed" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <Input
        label="Provider name"
        value={slug}
        onChange={(e) => setSlug(e.target.value)}
        placeholder="e.g., keycloak, okta"
        error={errors.slug}
      />
      <div className="flex flex-col gap-2">
        <Input
          label="Discovery URL"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://idp.example.com/realms/main"
          error={errors.url}
        />
        <div className="flex items-center gap-3">
          <Button
            type="button"
            size="sm"
            variant="outline"
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
      <Input
        label="Client ID"
        value={clientId}
        onChange={(e) => setClientId(e.target.value)}
        error={errors.clientId}
      />
      {editing && (
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <Checkbox
            checked={changeSecret}
            onCheckedChange={(v) => setChangeSecret(v === true)}
            aria-label="Update client secret"
          />
          Update client secret
        </label>
      )}
      {showSecret && (
        <Input
          label="Client secret"
          type="password"
          autoComplete="new-password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          error={errors.secret}
        />
      )}
      <Textarea
        label="Scopes"
        value={scopes}
        onChange={(e) => setScopes(e.target.value)}
      />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={pending}>
          {editing ? "Save changes" : "Create provider"}
        </Button>
      </div>
    </form>
  );
}
