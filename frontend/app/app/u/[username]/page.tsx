"use client";
/**
 * @file app/app/u/[username]/page.tsx
 * @brief @mention link target: resolves a username and forwards to the
 *        member profile.
 */
import { use, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { lookupUsername } from "@/lib/api/tags";

export default function UsernamePage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = use(params);
  const router = useRouter();
  const q = useQuery({
    queryKey: ["users", "lookup", username],
    queryFn: () => lookupUsername(username),
    retry: false,
  });
  useEffect(() => {
    if (q.data) router.replace(`/app/members/${q.data.id}`);
  }, [q.data, router]);
  if (q.isError)
    return (
      <EmptyState
        icon={Users}
        title="Member not found"
        description={`No one here goes by @${username}.`}
      />
    );
  return <p className="p-6 text-sm text-muted">Opening @{username}…</p>;
}
