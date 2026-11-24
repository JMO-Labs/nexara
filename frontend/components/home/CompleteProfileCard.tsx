"use client";
/**
 * @file components/home/CompleteProfileCard.tsx
 * @brief Home nudge for members who skipped profile setup (no photo,
 *        birthday or relations). Dismissal is stored in user settings.
 */
import Link from "next/link";
import { X } from "lucide-react";
import { Panel } from "@/components/ui/page";
import {
  useMyProfile,
  useUpdateSettings,
  useUserSettings,
} from "@/hooks/useSettings";
import { useRelations } from "@/hooks/useRelations";
import { useOnboarding } from "@/hooks/useOnboarding";

export function CompleteProfileCard() {
  const { data: onboarding } = useOnboarding();
  const { data: settings } = useUserSettings();
  const { data: me } = useMyProfile();
  const relations = useRelations(me?.id ?? "", !!me?.id);
  const update = useUpdateSettings();
  if (!onboarding?.done || !settings || !me || !relations.data) return null;
  if (settings.profile_card_dismissed) return null;
  const todo = [
    !me.avatar_url && "a profile photo",
    !me.birthday && "your birthday",
    relations.data.length === 0 && "your family",
  ].filter(Boolean) as string[];
  if (todo.length === 0) return null;
  return (
    <Panel as="div" className="mb-3 flex items-start gap-3">
      <div className="min-w-0 flex-1">
        <h2 className="text-sm font-semibold">Complete your profile</h2>
        <p className="mt-0.5 text-xs text-muted">
          Add {todo.join(", ")} so people can find and recognise you.{" "}
          <Link href="/app/welcome" className="font-medium underline">
            Finish setup
          </Link>
        </p>
      </div>
      <button
        type="button"
        aria-label="Dismiss profile reminder"
        className="focus-visible:outline-accent rounded-full p-2 text-muted focus-visible:outline-2"
        onClick={() => update.mutate({ profile_card_dismissed: true })}
      >
        <X className="size-4" aria-hidden />
      </button>
    </Panel>
  );
}
