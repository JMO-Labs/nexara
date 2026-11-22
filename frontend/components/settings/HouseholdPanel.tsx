"use client";
/**
 * @file components/settings/HouseholdPanel.tsx
 * @brief Settings "Family & pets": list, add and edit household members.
 */
import * as React from "react";
import { PawPrint, UserPlus } from "lucide-react";
import { Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { HouseholdCards } from "@/components/household/HouseholdCards";
import { HouseholdEditor } from "@/components/household/HouseholdEditor";
import { useUserHousehold } from "@/hooks/useHousehold";
import type { HouseholdKind, HouseholdMember } from "@/lib/api/household";
import { useSession } from "@/stores/session";

/** @brief Household management panel. */
export function HouseholdPanel() {
  const me = useSession((s) => s.user?.id);
  const { data = [] } = useUserHousehold(me);
  const [editing, setEditing] = React.useState<{
    member: HouseholdMember | null;
    kind: HouseholdKind;
  } | null>(null);

  return (
    <Panel title="Family & pets">
      <p className="mb-3 text-sm text-muted">
        Kids, relatives and pets without an account. They can be tagged in
        photos, and their birthdays show up for family.
      </p>
      {data.length > 0 && (
        <HouseholdCards
          items={data}
          onEdit={(m) => setEditing({ member: m, kind: m.kind })}
        />
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setEditing({ member: null, kind: "person" })}
        >
          <UserPlus className="size-4" aria-hidden /> Add family member
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setEditing({ member: null, kind: "pet" })}
        >
          <PawPrint className="size-4" aria-hidden /> Add pet
        </Button>
      </div>
      {editing && (
        <HouseholdEditor
          member={editing.member}
          kind={editing.kind}
          onClose={() => setEditing(null)}
        />
      )}
    </Panel>
  );
}
