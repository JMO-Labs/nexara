"use client";
/**
 * @file components/onboarding/steps/FamilyStep.tsx
 * @brief Wizard step 4: add relations to other members and household members.
 */
import * as React from "react";
import { UserPlus } from "lucide-react";
import { Button } from "@/components/ui";
import { HouseholdPanel } from "@/components/settings/HouseholdPanel";
import { AddRelationDialog } from "@/components/relations/AddRelationDialog";
import { useFeature } from "@/hooks/useFeature";

export function FamilyStep() {
  const relationsOn = useFeature("relations");
  const [open, setOpen] = React.useState(false);
  return (
    <div className="space-y-4">
      {relationsOn && (
        <>
          <Button variant="ghost" onClick={() => setOpen(true)}>
            <UserPlus className="size-4" aria-hidden /> Add a relation
          </Button>
          <AddRelationDialog open={open} onClose={() => setOpen(false)} />
        </>
      )}
      <HouseholdPanel />
    </div>
  );
}
