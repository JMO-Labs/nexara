"use client";
/**
 * @file components/lists/pages/ListsBrowseView.tsx
 * @brief /app/lists: list grid with visibility filter and sort.
 */
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LayoutTemplate, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Segmented, Toolbar } from "@/components/ui/page";
import { useCommunityId } from "@/hooks/useCommunityId";
import { ListCardGrid, type ListSort } from "../ListCardGrid";
import { PageHeader } from "./PageChrome";

const ALL = "all";
const VISIBILITY = [
  { value: ALL, label: "All lists" },
  { value: "community", label: "Community" },
  { value: "subgroup", label: "Group" },
  { value: "private", label: "Private" },
];
const SORTS: { value: ListSort; label: string }[] = [
  { value: "updated", label: "Recently updated" },
  { value: "created", label: "Newest" },
  { value: "title", label: "Title" },
];

/** @brief Lists overview page body. */
export function ListsBrowseView() {
  const router = useRouter();
  const communityId = useCommunityId();
  const [visibility, setVisibility] = useState(ALL);
  const [sortBy, setSortBy] = useState<ListSort>("updated");
  return (
    <div className="flex flex-col">
      <PageHeader
        crumbs={[{ label: "Lists" }]}
        title="Lists"
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/app/lists/templates">
                <LayoutTemplate aria-hidden className="size-4" />
                Templates
              </Link>
            </Button>
            <Button asChild>
              <Link href="/app/lists/new">
                <Plus aria-hidden className="size-4" />
                New list
              </Link>
            </Button>
          </>
        }
      />
      <Toolbar>
        <Segmented
          label="Visibility"
          value={visibility}
          onChange={setVisibility}
          options={VISIBILITY}
        />
        <Segmented
          label="Sort by"
          value={sortBy}
          onChange={setSortBy}
          options={SORTS}
        />
      </Toolbar>
      <ListCardGrid
        communityId={communityId}
        visibility={visibility === ALL ? undefined : visibility}
        sortBy={sortBy}
        onOpen={(l) => router.push(`/app/lists/${l.id}`)}
      />
    </div>
  );
}
