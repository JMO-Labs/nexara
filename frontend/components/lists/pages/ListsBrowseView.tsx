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
import { Option, Select } from "@/components/ui/Select";
import { useCommunityId } from "@/hooks/useCommunityId";
import { ListCardGrid, type ListSort } from "../ListCardGrid";
import { PageHeader } from "./PageChrome";

const ALL = "all";

/** @brief Lists overview page body. */
export function ListsBrowseView() {
  const router = useRouter();
  const communityId = useCommunityId();
  const [visibility, setVisibility] = useState(ALL);
  const [sortBy, setSortBy] = useState<ListSort>("updated");
  return (
    <div className="flex flex-col gap-6">
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
      <div className="grid gap-3 sm:max-w-md sm:grid-cols-2">
        <Select
          label="Visibility"
          value={visibility}
          onValueChange={setVisibility}
        >
          <Option value={ALL}>All lists</Option>
          <Option value="community">Community</Option>
          <Option value="subgroup">Group</Option>
          <Option value="private">Private</Option>
        </Select>
        <Select
          label="Sort by"
          value={sortBy}
          onValueChange={(v) => setSortBy(v as ListSort)}
        >
          <Option value="updated">Recently updated</Option>
          <Option value="created">Newest</Option>
          <Option value="title">Title</Option>
        </Select>
      </div>
      <ListCardGrid
        communityId={communityId}
        visibility={visibility === ALL ? undefined : visibility}
        sortBy={sortBy}
        onOpen={(l) => router.push(`/app/lists/${l.id}`)}
      />
    </div>
  );
}
