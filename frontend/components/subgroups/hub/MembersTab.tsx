/**
 * @file components/subgroups/hub/MembersTab.tsx
 * @brief Group members tab lifted from MembersList.
 */
"use client";

import * as React from "react";
import { MembersList } from "../MembersList";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface MembersTabProps {
  subgroup: SubgroupDetail;
}

export function MembersTab({ subgroup }: MembersTabProps) {
  const canManage =
    subgroup.my_role === "owner" || subgroup.my_role === "moderator";

  return (
    <MembersList
      slug={subgroup.slug}
      canManage={canManage}
      viewerRole={subgroup.my_role ?? null}
    />
  );
}

export default MembersTab;
