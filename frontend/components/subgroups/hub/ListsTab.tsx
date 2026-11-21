"use client";
/**
 * @file components/subgroups/hub/ListsTab.tsx
 * @brief Lists tab: lists belonging to this group, with a New list action.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ListCardGrid } from "@/components/lists/ListCardGrid";
import { useCommunityId } from "@/hooks/useCommunityId";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface ListsTabProps {
  subgroup: SubgroupDetail;
}

/**
 * @brief Group hub Lists tab body.
 * @param props subgroup whose lists to show
 * @return tab element
 */
export function ListsTab({ subgroup }: ListsTabProps) {
  const router = useRouter();
  const communityId = useCommunityId();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button asChild>
          <Link href={`/app/lists/new?subgroup=${subgroup.id}`}>
            <Plus aria-hidden className="size-4" />
            New list
          </Link>
        </Button>
      </div>
      <ListCardGrid
        communityId={communityId}
        subgroupId={subgroup.id}
        onOpen={(l) => router.push(`/app/lists/${l.id}`)}
      />
    </div>
  );
}
