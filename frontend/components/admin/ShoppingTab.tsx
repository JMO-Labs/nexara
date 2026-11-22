"use client";
/**
 * @file components/admin/ShoppingTab.tsx
 * @brief Admin Shopping tab: Amazon Associates / Creators API keys that turn
 *        on live Amazon prices and pictures for wishlist links.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Input } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/adminShop";
import { AdminLoading, AdminNotice } from "./AdminState";

const KEY = ["admin", "shop", "amazon"];
const MARKETS = [
  "www.amazon.com",
  "www.amazon.ca",
  "www.amazon.com.mx",
  "www.amazon.co.uk",
  "www.amazon.de",
  "www.amazon.fr",
  "www.amazon.it",
  "www.amazon.es",
  "www.amazon.co.jp",
  "www.amazon.com.au",
  "www.amazon.in",
];
const STATUS = {
  admin: "On, using the keys saved here.",
  server: "On, using keys from the server environment.",
  none: "Off. Amazon links show as plain links; people type the price.",
};

function SetupSteps() {
  return (
    <Panel title="How to get your keys" className="flex flex-col gap-2">
      <ol className="ml-5 list-decimal space-y-1.5 text-sm text-muted">
        <li>
          Join Amazon Associates (free) at{" "}
          <a
            className="text-accent underline"
            href="https://affiliate-program.amazon.com/"
            target="_blank"
            rel="noreferrer"
          >
            affiliate-program.amazon.com
          </a>
          . Your tracking ID (like <code>yourname-20</code>) is shown at the top
          right of Associates Central.
        </li>
        <li>
          In Associates Central, open Tools, then Creators API, and create
          credentials. Copy the client ID and secret; the secret is shown once.
        </li>
        <li>Paste all three below, pick your Amazon store, save, then test.</li>
      </ol>
      <p className="text-sm text-muted">
        Amazon may only grant API access after your account has a few qualifying
        sales, and can pause it if none come through your links for a while.
        Links on wishlists carry your tracking ID, as Amazon requires.
      </p>
    </Panel>
  );
}

/** @brief Amazon settings form with status and connection test. */
function AmazonForm({ data }: { data: api.AmazonSettings }) {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const [form, setForm] = useState({
    client_id: data.client_id,
    partner_tag: data.partner_tag,
    marketplace: data.marketplace,
  });
  const [secret, setSecret] = useState("");
  const save = useMutation({
    mutationFn: () =>
      api.putAmazon(secret ? { ...form, client_secret: secret } : form),
    onSuccess: (d) => {
      qc.setQueryData(KEY, d);
      setSecret("");
      push({ variant: "success", message: "Amazon settings saved" });
    },
    onError: (err) => push({ variant: "danger", message: formatApiError(err) }),
  });
  const test = useMutation({ mutationFn: api.testAmazon });
  const set =
    (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Amazon prices" className="flex flex-col gap-4">
        <p className="text-sm text-muted">
          With Amazon keys, wishlist items linked to Amazon show the live price
          and picture, refreshed hourly. Other shops work without keys.
        </p>
        <p role="status" className="text-sm font-medium">
          {STATUS[data.source ?? "none"]}
        </p>
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <Input
            label="Tracking ID (partner tag)"
            value={form.partner_tag}
            onChange={set("partner_tag")}
            placeholder="yourname-20"
            autoComplete="off"
          />
          <Input
            label="Client ID"
            value={form.client_id}
            onChange={set("client_id")}
            autoComplete="off"
          />
          <Input
            label="Client secret"
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder={
              data.has_secret ? "Saved. Leave blank to keep it." : ""
            }
            autoComplete="new-password"
          />
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Amazon store
            <select
              value={form.marketplace}
              onChange={set("marketplace")}
              className="glass-item h-11 rounded-full px-4 text-sm font-normal focus-visible:outline-2 focus-visible:outline-accent"
            >
              {MARKETS.map((m) => (
                <option key={m} value={m}>
                  {m.replace("www.", "")}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving..." : "Save"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => test.mutate()}
              disabled={test.isPending}
            >
              {test.isPending ? "Testing..." : "Test connection"}
            </Button>
            {test.isError && (
              <AdminNotice tone="error">Connection test failed.</AdminNotice>
            )}
            {test.data && (
              <span
                role="status"
                className={
                  test.data.success ? "text-sm text-ink" : "text-sm text-danger"
                }
              >
                {test.data.message}
              </span>
            )}
          </div>
        </form>
      </Panel>
      <SetupSteps />
    </div>
  );
}

/** @brief Shopping tab: loads saved settings, then the form. */
export function ShoppingTab() {
  const { data } = useQuery({ queryKey: KEY, queryFn: api.getAmazon });
  return data ? <AmazonForm data={data} /> : <AdminLoading />;
}
