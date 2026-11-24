"use client";
/**
 * @file components/compose/NsfwToggle.tsx
 * @brief "NSFW" switch for composers/uploads. Hidden unless the viewer is an
 *        adult and the nsfw feature is on.
 */
import { Switch } from "@/components/ui";
import { useFeature } from "@/hooks/useFeature";
import { useSession } from "@/stores/session";

export interface NsfwToggleProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  /** Locked by a moderator: author cannot clear. */
  locked?: boolean;
}

/**
 * @brief Adult-only NSFW switch with help text.
 * @return switch row or null
 */
export function NsfwToggle({ checked, onChange, locked }: NsfwToggleProps) {
  const adult = useSession((s) => s.user?.age_group === "adult");
  const on = useFeature("nsfw");
  if (!adult || !on) return null;
  return (
    <div className="flex items-start gap-3">
      <Switch
        aria-label="NSFW"
        checked={checked || !!locked}
        disabled={locked}
        onCheckedChange={onChange}
      />
      <div className="text-sm">
        <p className="font-medium">NSFW</p>
        <p className="text-xs text-muted">
          Hidden from children and teens. Adults see it blurred until they tap.
        </p>
      </div>
    </div>
  );
}

export default NsfwToggle;
