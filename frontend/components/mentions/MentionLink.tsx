"use client";
/**
 * @file components/mentions/MentionLink.tsx
 * @brief Rendered @mention: a profile link, or a group chip when the name is
 *        a group slug and no member has that username (same rule as the
 *        server). Falls back to a profile link outside a QueryClient.
 */
import * as React from "react";
import Link from "next/link";
import { QueryClientContext } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { useMembersList } from "@/hooks/useMembersList";
import { useSubgroupList } from "@/hooks/useSubgroups";

const userCls = "font-medium !no-underline hover:!underline";
const stop = (e: React.MouseEvent) => e.stopPropagation();

function Smart({
  name,
  children,
}: {
  name: string;
  children: React.ReactNode;
}) {
  const { data: members } = useMembersList();
  const { data: groups } = useSubgroupList();
  const group =
    !members?.some((u) => u.username === name) &&
    groups?.find((g) => g.slug === name);
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
      className="inline-flex items-center gap-1 rounded-full bg-[color-mix(in_srgb,var(--nx-blue)_16%,transparent)] px-2 py-px align-baseline text-[0.9em] font-medium !no-underline hover:!underline"
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
