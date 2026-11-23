"use client";
/**
 * @file components/admin/GoogleConnect.tsx
 * @brief "Connect Google account" for Gmail via OAuth (no app password).
 *        The client secret is write-only.
 */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Input } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/adminEmail";

/** @brief Connect/reconnect button plus optional own Google client fields. */
export function GoogleConnect({ data }: { data: api.EmailSettings }) {
  const push = useToasts((s) => s.push);
  const qc = useQueryClient();
  const [clientId, setClientId] = useState(data.google_client_id);
  const [secret, setSecret] = useState("");
  const hasClient =
    data.google_env_client ||
    (!!data.google_client_id && data.has_google_client_secret);
  const connected = data.auth === "google_oauth" && data.has_google_refresh;

  const saveClient = useMutation({
    mutationFn: () =>
      api.putEmail({
        google_client_id: clientId,
        ...(secret ? { google_client_secret: secret } : {}),
      }),
    onSuccess: (d) => {
      setSecret("");
      qc.setQueryData(["admin", "email"], d);
      push({ variant: "success", message: "Google client saved" });
    },
    onError: (err) => push({ variant: "danger", message: formatApiError(err) }),
  });
  const connect = useMutation({
    mutationFn: api.googleStart,
    onSuccess: ({ url }) => window.location.assign(url),
    onError: (err) => push({ variant: "danger", message: formatApiError(err) }),
  });

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border p-4">
      <h3 className="text-sm font-semibold">Google account</h3>
      <p role="status" className="text-sm text-muted">
        {connected
          ? `Connected as ${data.user}. Mail is sent through this account without a password.`
          : "Sign in with Google instead of using an app password."}
      </p>
      {!data.google_env_client && (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-muted">
            Create an OAuth client (type Web application) in Google Cloud and
            allow this redirect URI:{" "}
            <code>{`${typeof window === "undefined" ? "" : window.location.origin}/api/v1/admin/email/google/callback`}</code>
          </p>
          <Input
            label="Google client ID"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            autoComplete="off"
          />
          <Input
            label="Google client secret"
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder={
              data.has_google_client_secret
                ? "Saved. Leave blank to keep it."
                : ""
            }
            autoComplete="new-password"
          />
          <div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => saveClient.mutate()}
              disabled={saveClient.isPending || !clientId}
            >
              Save client
            </Button>
          </div>
        </div>
      )}
      <div>
        <Button
          type="button"
          onClick={() => connect.mutate()}
          disabled={connect.isPending || !hasClient}
        >
          {connected ? "Reconnect Google account" : "Connect Google account"}
        </Button>
      </div>
    </div>
  );
}
