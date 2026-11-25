"use client";
/**
 * @file components/admin/plugins/InstallUrlDialog.tsx
 * @brief Install a plugin from a package (URL + SHA-256, run by the plugin
 *        host) or, as "External plugin (advanced)", from a manifest URL. The
 *        first submit sends no approvals; the backend answers
 *        `scopes_not_approved` with what the plugin wants, which the admin
 *        must tick before it is resent.
 */
import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Checkbox, Input, Modal } from "@/components/ui";
import { ApiError, formatApiError } from "@/lib/api/errors";
import { installPackage, installPlugin } from "@/lib/api/plugins";

type Mode = "package" | "url";

interface Review {
  scopes: string[];
  events: string[];
  egress: string[];
}

const SCOPE_TEXT: Record<string, string> = {
  "posts:read": "Read posts",
  "posts:write": "Create posts",
  "comments:read": "Read comments",
  "comments:write": "Create comments",
};
const EVENT_TEXT: Record<string, string> = {
  "post.created": "A post is created",
  "comment.created": "A comment is created",
  mention: "The plugin is @mentioned",
};

const strs = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];

/**
 * @brief Install dialog.
 * @param open visibility
 * @param onClose close handler
 * @param onInstalled called after a successful install
 * @return modal
 */
export function InstallUrlDialog({
  open,
  onClose,
  onInstalled,
}: {
  open: boolean;
  onClose: () => void;
  onInstalled?: () => void;
}) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<Mode>("package");
  const [pkgUrl, setPkgUrl] = useState("");
  const [sha, setSha] = useState("");
  const [manifest, setManifest] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [review, setReview] = useState<Review | null>(null);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");

  const install = useMutation({
    mutationFn: (approved: string[]) =>
      mode === "package"
        ? installPackage({
            package_url: pkgUrl.trim(),
            sha256: sha.trim(),
            approved_scopes: approved,
          })
        : installPlugin({
            manifest_url: manifest.trim(),
            endpoint_url: endpoint.trim(),
            approved_scopes: approved,
          }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin", "plugins"] });
      onInstalled?.();
      onClose();
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === "scopes_not_approved") {
        setReview({
          scopes: strs(e.details?.scopes),
          events: strs(e.details?.events),
          egress: strs(e.details?.egress),
        });
        setTicked(new Set());
        setError("");
      } else if (
        e instanceof ApiError &&
        e.code === "plugin_host_not_configured"
      ) {
        setError(
          "Package installs need the plugin host, which is not set up on this server. Ask whoever runs Nexara to enable it, or use External plugin (advanced).",
        );
      } else setError(formatApiError(e));
    },
  });

  const all = review !== null && review.scopes.every((s) => ticked.has(s));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (review && !all) return;
    install.mutate(review ? review.scopes : []);
  };
  const toggle = (s: string, on: boolean) =>
    setTicked((t) => {
      const n = new Set(t);
      if (on) n.add(s);
      else n.delete(s);
      return n;
    });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Install plugin"
      description="Install a plugin package, or connect a plugin you run yourself."
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <fieldset className="flex flex-col gap-2" disabled={review !== null}>
          <legend className="text-sm font-semibold">Install from</legend>
          {(
            [
              ["package", "Plugin package"],
              ["url", "External plugin (advanced)"],
            ] as const
          ).map(([m, label]) => (
            <label key={m} className="flex min-h-11 items-center gap-2 text-sm">
              <input
                type="radio"
                name="install-mode"
                value={m}
                checked={mode === m}
                onChange={() => {
                  setMode(m);
                  setError("");
                }}
              />
              {label}
            </label>
          ))}
        </fieldset>
        {mode === "package" ? (
          <>
            <Input
              label="Package URL"
              type="url"
              required
              hint="An https link to the plugin's .tar.gz package."
              value={pkgUrl}
              disabled={review !== null}
              onChange={(e) => setPkgUrl(e.target.value)}
            />
            <Input
              label="SHA-256"
              required
              pattern="[0-9a-fA-F]{64}"
              hint="The package checksum published by the plugin author."
              value={sha}
              disabled={review !== null}
              onChange={(e) => setSha(e.target.value)}
            />
          </>
        ) : (
          <>
            <Input
              label="Manifest URL"
              type="url"
              required
              value={manifest}
              disabled={review !== null}
              onChange={(e) => setManifest(e.target.value)}
            />
            <Input
              label="Endpoint URL"
              type="url"
              required
              hint="Where Nexara sends events to the plugin."
              value={endpoint}
              disabled={review !== null}
              onChange={(e) => setEndpoint(e.target.value)}
            />
          </>
        )}
        {review && (
          <div className="flex flex-col gap-3">
            <fieldset className="flex flex-col gap-2">
              <legend className="text-sm font-semibold">
                This plugin asks to
              </legend>
              {review.scopes.map((s) => (
                <label key={s} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={ticked.has(s)}
                    onCheckedChange={(c) => toggle(s, c === true)}
                  />
                  {SCOPE_TEXT[s] ?? s}
                </label>
              ))}
            </fieldset>
            {review.events.length > 0 && (
              <div className="text-sm">
                <p className="font-semibold">It is notified when</p>
                <ul className="list-disc pl-5">
                  {review.events.map((ev) => (
                    <li key={ev}>{EVENT_TEXT[ev] ?? ev}</li>
                  ))}
                </ul>
              </div>
            )}
            {review.egress.length > 0 && (
              <div className="text-sm">
                <p className="font-semibold">It may contact these hosts</p>
                <ul className="list-disc pl-5">
                  {review.egress.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={install.isPending}
            disabled={review !== null && !all}
          >
            {review ? "Approve and install" : "Continue"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
