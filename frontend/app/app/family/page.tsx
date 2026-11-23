/**
 * @file app/app/family/page.tsx
 * @brief Family tree page: relatives around you with pan/zoom and a list view.
 */
"use client";

import * as React from "react";
import { EmptyState, Skeleton } from "@/components/ui";
import { PageHeader } from "@/components/ui/page";
import { FamilyTree } from "@/components/tree/FamilyTree";
import { useFeature } from "@/hooks/useFeature";
import { useFamilyTree } from "@/hooks/useTree";

export default function FamilyRoute() {
  const on = useFeature("family_tree");
  const [gens, setGens] = React.useState(3);
  const { data, isLoading } = useFamilyTree(gens);
  if (!on) return null;
  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-5 pb-8">
      <PageHeader
        title="Family"
        description="Who is related to whom. Add relations from a profile."
      />
      {isLoading && <Skeleton className="h-72 w-full" />}
      {data && data.nodes.length <= 1 && data.edges.length === 0 ? (
        <EmptyState
          title="No relatives yet"
          description="Open a profile and choose Add relation to start your tree."
        />
      ) : (
        data && (
          <FamilyTree
            data={data}
            onExpand={() => setGens((g) => Math.min(10, g + 2))}
          />
        )
      )}
    </div>
  );
}
