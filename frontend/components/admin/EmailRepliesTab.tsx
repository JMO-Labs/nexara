"use client";
/**
 * @file components/admin/EmailRepliesTab.tsx
 * @brief Admin "Email replies" tab: mailbox settings for reply-by-email,
 *        a connection test, and short setup steps. The password is write-only.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Input } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/adminEmailReply";
import { AdminLoading, AdminNotice } from "./AdminState";

const KEY = ["admin", "email-reply"];

function SetupSteps() {
  return (
    <Panel title="Setup steps" className="flex flex-col gap-2">
      <ol className="ml-5 list-decimal space-y-1.5 text-sm text-muted">
        <li>
          Create a mailbox just for replies, for example{" "}
          <code>reply@yourdomain.com</code>. Nothing else should use it: every
          message is deleted after it is read.
        </li>
        <li>Turn on IMAP access for that mailbox in your mail provider.</li>
        <li>
          Use an app password if the provider offers one (Gmail and Outlook
          require it with two-step sign-in). Paste it above.
        </li>
        <li>
          Make sure mail to <code>reply+anything@yourdomain.com</code> reaches
          the mailbox: turn on plus-addressing, or set a catch-all.
        </li>
        <li>
          Save, press Test connection, then turn on &quot;Reply by email&quot;
          under Features.
        </li>
      </ol>
      <p className="text-sm text-muted">
        Members then answer a comment, mention or new-post email by replying to
        it. The reply is posted as their comment. Replies from any other address
        are ignored.
      </p>
    </Panel>
  );
}

/** @brief Settings form with connection test. */
function ReplyForm({ data }: { data: api.EmailReplySettings }) {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const [form, setForm] = useState({
    imap_host: data.imap_host,
    imap_port: String(data.imap_port),
    imap_user: data.imap_user,
    reply_address: data.reply_address,
  });
  const [password, setPassword] = useState("");
  const save = useMutation({
    mutationFn: () => {
      const body: api.EmailReplyUpdate = {
        ...form,
        imap_port: 993,
      };
      if (password) body.imap_password = password;
      return api.putEmailReply(body);
    },
    onSuccess: (d) => {
      qc.setQueryData(KEY, d);
      setPassword("");
      push({ variant: "success", message: "Email reply settings saved" });
    },
    onError: (err) => push({ variant: "danger", message: formatApiError(err) }),
  });
  const test = useMutation({ mutationFn: api.testEmailReply });
  const set =
    (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Reply by email" className="flex flex-col gap-4">
        <p className="text-sm text-muted">
          Lets members reply to notification emails to comment on a post. Off
          until you turn it on under Features.
        </p>
        <p role="status" className="text-sm font-medium">
          {data.configured
            ? "Mailbox settings are complete."
            : "Fill in every field to finish setup."}
        </p>
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <Input
            label="Reply address"
            type="email"
            value={form.reply_address}
            onChange={set("reply_address")}
            placeholder="reply@yourdomain.com"
            autoComplete="off"
          />
          <Input
            label="IMAP server"
            value={form.imap_host}
            onChange={set("imap_host")}
            placeholder="imap.yourdomain.com"
            autoComplete="off"
          />
          <Input
            label="IMAP port (SSL)"
            value="993"
            readOnly
            hint="Replies are read over IMAP with SSL on port 993."
          />
          <Input
            label="Mailbox user name"
            value={form.imap_user}
            onChange={set("imap_user")}
            autoComplete="off"
          />
          <Input
            label="Mailbox password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={
              data.has_password ? "Saved. Leave blank to keep it." : ""
            }
            autoComplete="new-password"
          />
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

/** @brief Email replies tab: loads saved settings, then the form. */
export function EmailRepliesTab() {
  const { data } = useQuery({ queryKey: KEY, queryFn: api.getEmailReply });
  return data ? <ReplyForm data={data} /> : <AdminLoading />;
}
