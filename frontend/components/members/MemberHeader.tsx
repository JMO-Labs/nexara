"use client";
/**
 * @file components/members/MemberHeader.tsx
 * @brief Profile header panel: avatar, names, bio, shared groups, actions.
 */
import * as React from "react";
import { format, parseISO } from "date-fns";
import { useRouter } from "next/navigation";
import { MoreHorizontal } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Panel } from "@/components/ui/page";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/Popover";
import { NudgeButton } from "@/components/engagement/NudgeButton";
import { BlockButton } from "@/components/common/BlockButton";
import { GroupChips } from "@/components/members/GroupChips";
import { FavoriteButton } from "@/components/home/FavoriteButton";
import { useCreateDm } from "@/hooks/useChat";
import type { DirectoryPerson, UserProfile } from "@/lib/api/users";
import { groupColor } from "@/lib/groupColor";

export interface MemberHeaderProps {
  profile: UserProfile;
  connection?: DirectoryPerson | null;
  isSelf: boolean;
}

/**
 * @brief Header card of a member profile.
 * @param profile public profile
 * @param connection directory entry (shared groups, presence) if visible
 * @param isSelf hides social actions when viewing own profile
 * @return glass panel
 */
export function MemberHeader({
  profile,
  connection,
  isSelf,
}: MemberHeaderProps) {
  const router = useRouter();
  const dm = useCreateDm();
  const groups = connection?.shared_groups ?? [];
  const accent = groups.find(
    (g) => g.id === connection?.primary_group_id,
  )?.accent_color;
  const ring = groupColor(connection?.primary_group_id ?? null, accent);
  const subtitle = [profile.title, profile.pronouns, profile.location]
    .filter(Boolean)
    .join(" · ");

  const message = async () => {
    const channel = await dm.mutateAsync(profile.id);
    router.push(`/app/chat/${channel.id}`);
  };

  return (
    <Panel as="section" aria-label="Profile">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <span
          style={{ "--rc": ring } as React.CSSProperties}
          className="relative block shrink-0 self-start rounded-full ring-2 ring-[var(--rc)]"
        >
          <Avatar
            src={profile.avatar_url ?? undefined}
            name={profile.display_name}
            size="lg"
            className="size-16 text-xl md:size-20"
          />
          {connection?.online && (
            <i
              aria-hidden
              className="absolute right-0 bottom-0 size-4 rounded-full border-2 border-[var(--nx-glass-solid)] bg-[var(--nx-ok)]"
            />
          )}
        </span>
        <div className="min-w-0 flex-1">
          {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
          <p className="text-xs text-muted">
            {`Joined ${format(parseISO(profile.created_at), "MMM yyyy")}`}
          </p>
          {profile.bio && (
            <p className="mt-2 text-sm whitespace-pre-line text-ink">
              {profile.bio}
            </p>
          )}
          <div className="mt-3">
            <GroupChips groups={groups} max={6} />
          </div>
        </div>
        {!isSelf && (
          <div className="flex flex-wrap items-center gap-2 sm:shrink-0 sm:self-start">
            <button
              type="button"
              onClick={message}
              disabled={dm.isPending}
              className="min-h-11 rounded-full bg-surface-strong px-5 py-2 text-sm font-medium text-bg disabled:opacity-60"
            >
              Message
            </button>
            <FavoriteButton
              userId={profile.id}
              name={profile.display_name}
              className="size-11"
            />
            <NudgeButton userId={profile.id} />
            <Popover>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  aria-label="More actions"
                  className="glass-item grid size-11 place-items-center rounded-full text-ink"
                >
                  <MoreHorizontal className="size-5" aria-hidden="true" />
                </button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-48 p-2">
                <BlockButton
                  userId={profile.id}
                  displayName={profile.display_name}
                />
              </PopoverContent>
            </Popover>
          </div>
        )}
      </div>
    </Panel>
  );
}
