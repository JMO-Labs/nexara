/**
 * @file components/subgroups/hub/MemberOnlyGate.tsx
 * @brief Non-member view for restricted groups: cover + info + CTA.
 */
"use client";

import * as React from "react";
import { Button } from "@/components/ui";
import { CoverBand } from "./CoverBand";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface MemberOnlyGateProps {
  subgroup: SubgroupDetail;
}

/**
 * @brief Gate shown to non-members of invite-only / approval groups.
 * @param subgroup group detail
 * @return gate view
 */
export function MemberOnlyGate({ subgroup }: MemberOnlyGateProps) {
  const ctaText =
    subgroup.join_policy === "admin_approval"
      ? "Request to join"
      : "Invite required";

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-8">
      <CoverBand subgroup={subgroup} />
      <div className="flex flex-col gap-4 px-4 md:px-0">
        <h2 className="text-2xl font-black tracking-tight">{subgroup.name}</h2>
        {subgroup.description && (
          <p className="text-muted">{subgroup.description}</p>
        )}
        <Button disabled size="lg" className="mt-2">
          {ctaText}
        </Button>
      </div>
    </div>
  );
}

export default MemberOnlyGate;
