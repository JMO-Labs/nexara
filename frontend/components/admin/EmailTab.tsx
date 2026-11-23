"use client";
/**
 * @file components/admin/EmailTab.tsx
 * @brief Admin "Email" tab: outgoing SMTP settings with Gmail/Outlook presets
 *        and a test send. The password is write-only.
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Input } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/adminEmail";
import { AdminLoading } from "./AdminState";
import { GoogleConnect } from "./GoogleConnect";

const KEY = ["admin", "email"];

/** @brief Provider presets: host, port and security for the form. */
export const PRESETS = {
  gmail: {
    label: "Gmail",
    host: "smtp.gmail.com",
    port: 587,
    security: "starttls" as api.SmtpSecurity,
  },
  outlook: {
    label: "Outlook",
    host: "smtp.office365.com",
    port: 587,
    security: "starttls" as api.SmtpSecurity,
  },
};
type PresetId = keyof typeof PRESETS | "custom";
const APP_PASSWORD_URL = "https://myaccount.google.com/apppasswords";

function presetOf(host: string): PresetId {
  const hit = (Object.keys(PRESETS) as (keyof typeof PRESETS)[]).find(
    (k) => PRESETS[k].host === host,
  );
  return hit ?? "custom";
}

function Help({ preset }: { preset: PresetId }) {
  if (preset === "gmail")
    return (
      <p className="text-sm text-muted">
        Use your Gmail address as user name and an app password, not your normal
        password. Google only offers app passwords when 2-Step Verification is
        on.{" "}
        <a
          href={APP_PASSWORD_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="underline"
        >
          Create an app password
        </a>
        . Spaces in it are ignored.
      </p>
    );
  if (preset === "outlook")
    return (
      <p className="text-sm text-muted">
        Use your Microsoft 365 address and password (or an app password if
        two-step sign-in is on). SMTP sending must be enabled for the mailbox.
      </p>
    );
  return (
    <p className="text-sm text-muted">
      Enter the SMTP details from your mail provider. Port 587 normally uses
      STARTTLS, port 465 uses SSL.
    </p>
  );
}

/** @brief Settings form with test send. */
function EmailForm({ data }: { data: api.EmailSettings }) {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const [form, setForm] = useState({
    host: data.host,
    port: String(data.port),
    security: data.security,
    user: data.user,
    from_addr: data.from_addr,
    from_name: data.from_name,
  });
  const [preset, setPreset] = useState<PresetId>(presetOf(data.host));
  const [password, setPassword] = useState("");
  const [to, setTo] = useState("");
  const save = useMutation({
    mutationFn: () => {
      const body: api.EmailUpdate = { ...form, port: Number(form.port) };
      if (password) {
        body.password = password;
        body.auth = "password";
      }
      return api.putEmail(body);
    },
    onSuccess: (d) => {
      qc.setQueryData(KEY, d);
      setPassword("");
      push({ variant: "success", message: "Email settings saved" });
    },
    onError: (err) => push({ variant: "danger", message: formatApiError(err) }),
  });
  const test = useMutation({
    mutationFn: () => api.testEmail(to),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
  const set =
    (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));
  const pick = (id: PresetId) => {
    setPreset(id);
    if (id !== "custom") {
      const { host, port, security } = PRESETS[id];
      setForm((f) => ({ ...f, host, port: String(port), security }));
    }
  };

  return (
    <Panel title="Outgoing email" className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Used for invites, password resets, sign-in links and notifications.
        Settings saved here override the server environment.
      </p>
      <div
        role="group"
        aria-label="Provider preset"
        className="flex flex-wrap gap-2"
      >
        {([...Object.keys(PRESETS), "custom"] as PresetId[]).map((id) => (
          <Button
            key={id}
            type="button"
            size="sm"
            variant={preset === id ? "primary" : "secondary"}
            aria-pressed={preset === id}
            onClick={() => pick(id)}
          >
            {id === "custom" ? "Custom" : PRESETS[id].label}
          </Button>
        ))}
      </div>
      <Help preset={preset} />
      {preset === "gmail" && <GoogleConnect data={data} />}
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Input
          label="SMTP server"
          value={form.host}
          onChange={set("host")}
          placeholder="smtp.example.com"
          autoComplete="off"
        />
        <Input
          label="Port"
          type="number"
          value={form.port}
          onChange={set("port")}
        />
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Security
          <select
            value={form.security}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                security: e.target.value as api.SmtpSecurity,
              }))
            }
            className="h-11 rounded-full border border-border bg-transparent px-4"
          >
            <option value="starttls">STARTTLS (port 587)</option>
            <option value="ssl">SSL (port 465)</option>
            <option value="none">None</option>
          </select>
        </label>
        <Input
          label="User name"
          value={form.user}
          onChange={set("user")}
          autoComplete="off"
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={
            data.has_password ? "Saved. Leave blank to keep it." : ""
          }
          autoComplete="new-password"
        />
        <Input
          label="From address"
          type="email"
          value={form.from_addr}
          onChange={set("from_addr")}
          placeholder="noreply@yourdomain.com"
        />
        <Input
          label="From name"
          value={form.from_name}
          onChange={set("from_name")}
          placeholder="Optional"
        />
        <div>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? "Saving..." : "Save"}
          </Button>
        </div>
      </form>
      <div className="flex flex-col gap-3 border-t border-border pt-4">
        <Input
          label="Send test to"
          type="email"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="you@example.com"
        />
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={() => test.mutate()}
            disabled={test.isPending || !to}
          >
            {test.isPending ? "Sending..." : "Send test email"}
          </Button>
          {test.isError && (
            <span role="status" className="text-sm text-danger">
              Test failed.
            </span>
          )}
          {test.data && (
            <span
              role="status"
              className={
                test.data.ok ? "text-sm text-ink" : "text-sm text-danger"
              }
            >
              {test.data.ok ? "Test email sent." : test.data.error}
            </span>
          )}
        </div>
        {data.last_error && (
          <p className="text-sm text-danger">Last error: {data.last_error}</p>
        )}
        {data.last_ok_at && (
          <p className="text-sm text-muted">
            Last successful send: {new Date(data.last_ok_at).toLocaleString()}
          </p>
        )}
      </div>
    </Panel>
  );
}

/** @brief Email tab: loads saved settings, then the form. */
export function EmailTab() {
  const push = useToasts((s) => s.push);
  useEffect(() => {
    // Google redirects back here with ?google=connected|error.
    const url = new URL(window.location.href);
    const g = url.searchParams.get("google");
    if (!g) return;
    push(
      g === "connected"
        ? { variant: "success", message: "Google account connected" }
        : {
            variant: "danger",
            message: "Could not connect the Google account",
          },
    );
    url.searchParams.delete("google");
    window.history.replaceState(null, "", url);
  }, [push]);
  const { data } = useQuery({ queryKey: KEY, queryFn: api.getEmail });
  return data ? <EmailForm data={data} /> : <AdminLoading />;
}
