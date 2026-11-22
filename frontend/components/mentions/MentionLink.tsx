"use client";
/**
 * @file components/mentions/MentionLink.tsx
 * @brief Rendered @mention: a profile link; else a group chip (group slug)
 *        or a household chip (pet/family handle), in the server's order.
 *        Falls back to a profile link outside a QueryClient.
 */
import * as React from "react";
import Link from "next/link";
import { QueryClientContext } from "@tanstack/react-query";
import { PawPrint, User, Users } from "lucide-react";
import { useVisibleHousehold } from "@/hooks/useHousehold";
import { useMembersList } from "@/hooks/useMembersList";
import { useSubgroupList } from "@/hooks/useSubgroups";

const userCls = "font-medium !no-underline hover:!underline";
const stop = (e: React.MouseEvent) => e.stopPropagation();
const chipCls =
  "inline-flex items-center gap-1 rounded-full bg-[color-mix(in_srgb,var(--nx-blue)_16%,transparent)] px-2 py-px align-baseline text-[0.9em] font-medium !no-underline hover:!underline";

function Smart({
  name,
  children,
}: {
  name: string;
  children: React.ReactNode;
}) {
  const { data: members } = useMembersList();
  const { data: groups } = useSubgroupList();
  const { data: household } = useVisibleHousehold();
  const person = members?.some((u) => u.username === name);
  const group = !person && groups?.find((g) => g.slug === name);
  const home = !person && !group && household?.find((m) => m.handle === name);
  if (home) {
    const Icon = home.kind === "pet" ? PawPrint : User;
    return (
      <Link
        href={`/app/household/${home.id}`}
        onClick={stop}
        className={chipCls}
      >
        <Icon className="size-3.5" aria-hidden />
        {home.name}
      </Link>
    );
  }
  if (!group)
    return (
      <Link href={`/app/u/${name}`} className={userCls} onClick={stop}>
        {children}
      </Link>
    );
  return (
    <Link
      href={`/app/subgroups/${group.slug}`}
      onClick={stop}
      aria-label={`${group.name} group`}
      className={chipCls}
    >
      <Users className="size-3.5" aria-hidden />
      {group.name}
    </Link>
  );
}

/**
 * @brief Mention link for /app/u/<name> hrefs.
 * @param name username or group slug
 * @return link element
 */
export function MentionLink({
  name,
  children,
}: {
  name: string;
  children: React.ReactNode;
}) {
  if (!React.useContext(QueryClientContext))
    return (
      <Link href={`/app/u/${name}`} className={userCls} onClick={stop}>
        {children}
      </Link>
    );
  return <Smart name={name}>{children}</Smart>;
}
