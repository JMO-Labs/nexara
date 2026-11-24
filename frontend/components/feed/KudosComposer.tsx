"use client";
/**
 * @file components/feed/KudosComposer.tsx
 * @brief "Send Kudos" modal: recipient autocomplete, message, group select.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button, Modal, Textarea } from "@/components/ui";
import { controlClass } from "@/components/ui/Field";
import { cn } from "@/lib/utils";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useSendKudos } from "@/hooks/useKudos";
import { listUsers, type UserSummary } from "@/lib/api/users";

export interface KudosComposerProps {
  open: boolean;
  onClose: () => void;
}

/**
 * @brief Kudos composer modal.
 * @param open visibility
 * @param onClose called on cancel or after a successful send
 * @return modal element
 */
export function KudosComposer({ open, onClose }: KudosComposerProps) {
  const t = useTranslations("kudos");
  const [query, setQuery] = React.useState("");
  const [picked, setPicked] = React.useState<UserSummary | null>(null);
  const [message, setMessage] = React.useState("");
  const [subgroupId, setSubgroupId] = React.useState("");
  const listId = React.useId();
  const groups = useSubgroupList().data ?? [];
  const send = useSendKudos(picked);
  // Backend /users has no `q` filter yet: fetch a page, match client-side.
  const users = useQuery({
    queryKey: ["kudos", "users"],
    queryFn: () => listUsers(null, 100),
    enabled: open,
    staleTime: 60_000,
  });

  const q = query.trim().toLowerCase();
  const matches =
    q && !picked
      ? (users.data?.items ?? [])
          .filter((u) => !u.is_bot && u.display_name.toLowerCase().includes(q))
          .slice(0, 8)
      : [];

  const reset = () => {
    setQuery("");
    setPicked(null);
    setMessage("");
    setSubgroupId("");
  };
  const close = () => {
    reset();
    onClose();
  };
  const submit = () => {
    if (!picked) return;
    send.mutate(
      {
        recipient_id: picked.id,
        ...(message.trim() ? { message: message.trim() } : {}),
        ...(subgroupId ? { subgroup_id: subgroupId } : {}),
      },
      { onSuccess: close },
    );
  };

  return (
    <Modal
      open={open}
      onClose={close}
      title={t("title")}
      footer={
        <>
          <Button variant="ghost" onClick={close}>
            {t("cancel")}
          </Button>
          <Button onClick={submit} disabled={!picked || send.isPending}>
            {t("send")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="relative flex flex-col gap-1.5">
          <label htmlFor={`${listId}-in`} className="text-sm font-semibold">
            {t("recipient")}
          </label>
          <input
            id={`${listId}-in`}
            role="combobox"
            aria-expanded={matches.length > 0}
            aria-controls={listId}
            aria-autocomplete="list"
            autoComplete="off"
            value={query}
            placeholder={t("recipientPlaceholder")}
            onChange={(e) => {
              setQuery(e.target.value);
              setPicked(null);
            }}
            className={cn(controlClass, "h-11 rounded-full")}
          />
          {matches.length > 0 && (
            <ul
              id={listId}
              role="listbox"
              className="glass absolute top-full z-10 mt-1 w-full rounded-[20px] bg-[var(--nx-glass-solid)] p-1 shadow-[0_12px_32px_-12px_color-mix(in_srgb,var(--nx-ink)_35%,transparent)]"
            >
              {matches.map((u) => (
                <li
                  key={u.id}
                  role="option"
                  aria-selected={false}
                  tabIndex={0}
                  className="cursor-pointer rounded-lg px-3 py-2 hover:bg-bg focus-visible:bg-bg"
                  onClick={() => {
                    setPicked(u);
                    setQuery(u.display_name);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      setPicked(u);
                      setQuery(u.display_name);
                    }
                  }}
                >
                  {u.display_name}{" "}
                  <span className="text-xs opacity-70">@{u.username}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`${listId}-msg`} className="text-sm font-semibold">
            {t("message")}
          </label>
          <Textarea
            id={`${listId}-msg`}
            value={message}
            maxLength={2000}
            onChange={(e) => setMessage(e.target.value)}
          />
        </div>
        {groups.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor={`${listId}-sg`} className="text-sm font-semibold">
              {t("group")}
            </label>
            <select
              id={`${listId}-sg`}
              value={subgroupId}
              onChange={(e) => setSubgroupId(e.target.value)}
              className={cn(controlClass, "h-11 rounded-full")}
            >
              <option value="">{t("noGroup")}</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default KudosComposer;
