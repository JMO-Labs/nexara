"use client";
/**
 * @file components/admin/sso/TestLoginPanel.tsx
 * @brief SSO wizard step 5: sign in at the IdP in a popup and preview the result.
 *
 * Nothing is provisioned: the backend verifies the IdP response and reports
 * the claims, the mapped role/groups and whether sign-in would be allowed.
 * The popup (/sso-test) posts back a one-time result id, read here.
 */
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { AdminNotice } from "../AdminState";
import {
  SSO_TEST_MESSAGE,
  readTestLogin,
  startTestLogin,
  type TestLoginResult,
} from "@/lib/api/adminOauth";
import { formatApiError } from "@/lib/api/errors";

const REFUSALS: Record<string, string> = {
  sso_domain_not_allowed: "email domain is not allowed",
  sso_group_required: "user is not in the required group",
  sso_no_account: "no account exists and automatic creation is off",
  sso_account_disabled: "the account is disabled",
  sso_email_unverified: "the IdP did not verify the email",
  sso_email_unverified_local:
    "the matching local account has an unverified email",
};

/** @brief Give up waiting for the popup after this long (IdP error page, COOP). */
export const TEST_TIMEOUT_MS = 3 * 60 * 1000;
/** @brief How often to check whether the popup was closed. */
export const POLL_MS = 500;
/** @brief Grace after the popup closes for its postMessage to arrive. */
const CLOSE_GRACE_MS = 1500;

const CLOSED_MSG = "Test window closed before finishing.";
const TIMEOUT_MSG =
  "No result after 3 minutes. The identity provider may have shown an error, or blocked the reply to this page (Cross-Origin-Opener-Policy). Check the popup, then try again.";

const ACTIONS: Record<string, string> = {
  sign_in: "signs in to the linked account",
  link: "links to the existing account with this email",
  link_after_2fa: "links to the existing account after its second factor",
  create: "creates a new account",
};

/**
 * @brief One-line summary, e.g. "Would be: member of Smith Family, role member".
 * @param r test result
 * @return summary text
 */
export function describeResult(r: TestLoginResult): string {
  if (!r.outcome.allowed) {
    const why = REFUSALS[r.outcome.code ?? ""] ?? r.outcome.code ?? "refused";
    return `Would be refused: ${why}`;
  }
  const parts = r.subgroups.map((s) => `${s.role} of ${s.name}`);
  parts.push(`role ${r.role}`);
  return `Would be: ${parts.join(", ")}`;
}

/** @brief Props for TestLoginPanel. */
export interface TestLoginPanelProps {
  /** Saved provider id; null until the provider is created. */
  providerId: string | null;
}

/**
 * @brief Test-login launcher and report.
 * @param props see TestLoginPanelProps
 * @return panel
 */
export function TestLoginPanel({ providerId }: TestLoginPanelProps) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TestLoginResult | null>(null);
  const popup = useRef<Window | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  /** Stop watching the popup (result arrived, failed or gave up). */
  const stopWatch = () => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
  };

  useEffect(() => {
    const onMessage = async (e: MessageEvent) => {
      if (e.origin !== window.location.origin) return;
      const data = e.data as { type?: string; result?: string } | null;
      if (data?.type !== SSO_TEST_MESSAGE || !data.result) return;
      stopWatch();
      try {
        setResult(await readTestLogin(data.result));
        setError(null);
      } catch (err) {
        setError(formatApiError(err, "Could not read the test result."));
      } finally {
        setRunning(false);
      }
    };
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("message", onMessage);
      stopWatch();
    };
  }, []);

  /** Fail with msg (no result arrived in time). */
  const giveUp = (msg: string) => {
    stopWatch();
    setRunning(false);
    setError(msg);
  };

  /** Poll popup.closed and arm the overall timeout. */
  const watch = () => {
    stopWatch();
    const poll = () => {
      if (popup.current?.closed) {
        timers.current.push(
          setTimeout(() => giveUp(CLOSED_MSG), CLOSE_GRACE_MS),
        );
        return;
      }
      timers.current.push(setTimeout(poll, POLL_MS));
    };
    timers.current.push(setTimeout(poll, POLL_MS));
    timers.current.push(setTimeout(() => giveUp(TIMEOUT_MSG), TEST_TIMEOUT_MS));
  };

  if (!providerId) {
    return (
      <p className="text-sm text-muted">
        Save the provider first, then reopen it to run a test sign-in.
      </p>
    );
  }

  const run = async () => {
    setError(null);
    setResult(null);
    // Open synchronously in the click so popup blockers allow it.
    popup.current = window.open(
      "",
      "nexara-sso-test",
      "popup,width=520,height=720",
    );
    setRunning(true);
    try {
      const { authorize_url } = await startTestLogin(providerId);
      if (popup.current) popup.current.location.href = authorize_url;
      else popup.current = window.open(authorize_url, "nexara-sso-test");
      watch();
    } catch (err) {
      stopWatch();
      popup.current?.close();
      setRunning(false);
      setError(formatApiError(err, "Could not start the test sign-in."));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Tests the saved settings: save your changes first. Sign in at the
        identity provider in a popup. Nothing is created or changed; you see the
        claims and what Nexara would do.
      </p>
      <div>
        <Button type="button" onClick={run} loading={running}>
          Run test sign-in
        </Button>
      </div>
      {error && <AdminNotice tone="error">{error}</AdminNotice>}
      <div aria-live="polite">
        {result && (
          <div className="flex flex-col gap-3">
            <p className="font-medium">{describeResult(result)}</p>
            {result.outcome.allowed && result.outcome.action && (
              <p className="text-sm text-muted">
                Signing in {ACTIONS[result.outcome.action]}.
              </p>
            )}
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="text-muted">Email</dt>
              <dd>
                {result.identity.email ?? "none"}
                {result.identity.email && !result.identity.email_verified
                  ? " (unverified)"
                  : ""}
              </dd>
              <dt className="text-muted">Username</dt>
              <dd>{result.identity.username ?? "none"}</dd>
              <dt className="text-muted">Groups</dt>
              <dd>{result.identity.groups.join(", ") || "none"}</dd>
            </dl>
            <details>
              <summary className="cursor-pointer text-sm font-medium">
                Raw claims
              </summary>
              <pre
                aria-label="Raw claims"
                tabIndex={0}
                className="mt-2 max-h-72 overflow-auto rounded-2xl bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] p-3 text-xs"
              >
                {JSON.stringify(result.claims, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
