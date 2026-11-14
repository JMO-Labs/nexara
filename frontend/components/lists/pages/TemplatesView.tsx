"use client";
/**
 * @file components/lists/pages/TemplatesView.tsx
 * @brief /app/lists/templates: template gallery; clone creates a list
 *        and navigates to it.
 */
import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LayoutTemplate, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useCommunityId } from "@/hooks/useCommunityId";
import { useListTemplateClone, useListTemplates } from "@/hooks/useLists";
import { fromApi } from "@/lib/lists/templateAdapter";
import { TemplateGallery } from "../TemplateGallery";
import { ErrorCard, LISTS_CRUMB, PageHeader, PageSkeleton } from "./PageChrome";

/** @brief Template gallery page body. */
export function TemplatesView() {
  const router = useRouter();
  const communityId = useCommunityId();
  const { data, isLoading, error } = useListTemplates();
  const clone = useListTemplateClone(communityId);
  const templates = (data?.templates ?? []).map(fromApi);

  let body: ReactNode;
  if (isLoading) body = <PageSkeleton />;
  else if (error) body = <ErrorCard message="We couldn't load templates." />;
  else if (templates.length === 0)
    body = <EmptyState icon={LayoutTemplate} title="No templates yet" />;
  else
    body = (
      <TemplateGallery
        templates={templates}
        onEdit={(t) => router.push(`/app/lists/templates/${t.id}`)}
        onClone={(t) =>
          clone.mutate(
            { id: t.id },
            { onSuccess: (l) => router.push(`/app/lists/${l.id}`) },
          )
        }
      />
    );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        crumbs={[LISTS_CRUMB, { label: "Templates" }]}
        title="Templates"
        actions={
          <Button asChild>
            <Link href="/app/lists/templates/new">
              <Plus aria-hidden className="size-4" />
              New template
            </Link>
          </Button>
        }
      />
      {body}
    </div>
  );
}
