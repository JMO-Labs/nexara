"use client";
/**
 * @file components/members/MemberHeader.tsx
 * @brief Profile hero: banner (cover photo or group-colour wash), avatar
 *        overlapping it, name line, bio, shared groups and actions.
 */
import * as React from "react";
import Link from "next/link";
import { format, parseISO } from "date-fns";
import { useRouter } from "next/navigation";
import { MoreHorizontal, Pencil } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/Popover";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { NudgeButton } from "@/components/engagement/NudgeButton";
import { BlockButton } from "@/components/common/BlockButton";
import { MemorialHeader } from "@/components/memorials/MemorialHeader";
import { GroupChips } from "@/components/members/GroupChips";
import { FavoriteButton } from "@/components/home/FavoriteButton";
import { useCreateDm } from "@/hooks/useChat";
import type { DirectoryPerson, UserProfile } from "@/lib/api/users";
import { groupColor } from "@/lib/groupColor";

export interface MemberHeaderProps {
  profile: UserProfile;
  connection?: DirectoryPerson | null;
  isSelf: boolean;
  /** Presence line, e.g. "Active 8m ago". */
  status?: string;
}

/**
 * @brief Profile hero.
 * @param profile viewer-filtered profile
 * @param connection directory entry (shared groups, presence) if visible
 * @param isSelf shows Edit profile instead of social actions
 * @param status presence line
 * @return section element
 */
export function MemberHeader({
  profile,
  connection,
  isSelf,
  status,
}: MemberHeaderProps) {
  const router = useRouter();
  const dm = useCreateDm();
  const groups = connection?.shared_groups ?? [];
  const accent = groups.find(
    (g) => g.id === connection?.primary_group_id,
  )?.accent_color;
  const ring = groupColor(connection?.primary_group_id ?? null, accent);
  const meta = [
    `@${profile.username}`,
    profile.pronouns,
    profile.title,
    profile.location,
  ].filter(Boolean);

  const message = async () => {
    const channel = await dm.mutateAsync(profile.id);
    router.push(`/app/chat/${channel.id}`);
  };

  return (
    <section
      aria-label="Profile"
      className="glass overflow-hidden rounded-[32px]"
      style={{ "--rc": ring } as React.CSSProperties}
    >
      <div className="relative h-40 md:h-56">
        {profile.banner_media_id ? (
          <span className="absolute inset-0 block">
            <MediaThumb
              mediaId={profile.banner_media_id}
              alt=""
              objectPosition="50% 40%"
            />
          </span>
        ) : (
          <div
            aria-hidden
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(120% 140% at 15% 0%, color-mix(in srgb, var(--rc) 55%, transparent), transparent 60%), radial-gradient(90% 120% at 100% 100%, color-mix(in srgb, var(--nx-blue) 35%, transparent), transparent 65%)",
            }}
          />
        )}
        <div
          aria-hidden
          className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[var(--nx-glass-solid)]/70 to-transparent"
        />
      </div>

      {profile.memorialized_at && (
        <div className="px-5 pt-4 md:px-8">
          <MemorialHeader
            name={profile.display_name}
            handle={profile.username}
            born={profile.birthday}
            passedOn={profile.passed_on}
          />
        </div>
      )}
      <div className="relative px-5 pb-5 md:px-8 md:pb-7">
        <div className="-mt-12 flex flex-wrap items-end justify-between gap-3 md:-mt-14">
          <span className="relative block rounded-full ring-4 ring-[var(--nx-glass-solid)]">
            <Avatar
              src={profile.avatar_url ?? undefined}
              name={profile.display_name}
              size="lg"
              className="size-24 text-3xl md:size-28"
            />
            {connection?.online && (
              <i
                aria-hidden
                className="absolute right-1.5 bottom-1.5 size-5 rounded-full border-[3px] border-[var(--nx-glass-solid)] bg-[var(--nx-ok)]"
              />
            )}
          </span>
          <div className="flex flex-wrap items-center gap-2">
            {profile.memorialized_at ? null : isSelf ? (
              <Link
                href="/app/settings?tab=profile"
                className="glass-item flex min-h-11 items-center gap-2 rounded-full px-5 text-sm font-medium"
              >
                <Pencil className="size-4" aria-hidden /> Edit profile
              </Link>
            ) : (
              <>
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
              </>
            )}
          </div>
        </div>

        <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">
          {profile.display_name}
        </h1>
        <p className="mt-1 text-sm text-muted">
          {meta.join(" · ")}
          {status ? ` · ${status}` : ""}
          {` · Joined ${format(parseISO(profile.created_at), "MMM yyyy")}`}
        </p>
        {profile.bio && (
          <p className="mt-3 max-w-[65ch] text-[15px] leading-relaxed whitespace-pre-line">
            {profile.bio}
          </p>
        )}
        {groups.length > 0 && (
          <div className="mt-4">
            <GroupChips groups={groups} max={6} />
          </div>
        )}
      </div>
    </section>
  );
}
