"use client";
/**
 * @file components/lists/pages/TemplateDesignerView.tsx
 * @brief /app/lists/templates/new (create) and /templates/[id] (edit)
 *        wrappers around TemplateDesigner.
 */
import { useRouter } from "next/navigation";
import {
  useListTemplate,
  useListTemplateCreate,
  useListTemplateUpdate,
} from "@/hooks/useListDetail";
import { fromApi, toInput } from "@/lib/lists/templateAdapter";
import type { TemplateDraft } from "@/lib/lists/templateModel";
import { TemplateDesigner } from "../TemplateDesigner";
import {
  ErrorCard,
  LISTS_CRUMB,
  PageHeader,
  PageSkeleton,
  TEMPLATES_CRUMB,
} from "./PageChrome";

const GALLERY = "/app/lists/templates";
const EMPTY: TemplateDraft = { name: "", fields: [] };

/** @brief Create-template page body. */
export function TemplateNewView() {
  const router = useRouter();
  const create = useListTemplateCreate();
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        crumbs={[LISTS_CRUMB, TEMPLATES_CRUMB, { label: "New" }]}
        title="New template"
      />
      <TemplateDesigner
        initial={EMPTY}
        saving={create.isPending}
        onSave={(d) =>
          create.mutate(toInput(d), { onSuccess: () => router.push(GALLERY) })
        }
      />
    </div>
  );
}

/**
 * @brief Edit-template page body.
 * @param props template id
 * @return page
 */
export function TemplateEditView({ id }: { id: string }) {
  const router = useRouter();
  const { data, isLoading, error } = useListTemplate(id);
  const update = useListTemplateUpdate();
  if (isLoading) return <PageSkeleton />;
  if (error || !data)
    return <ErrorCard message="We couldn't load this template." />;
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        crumbs={[LISTS_CRUMB, TEMPLATES_CRUMB, { label: data.name }]}
        title="Edit template"
      />
      <TemplateDesigner
        key={data.id}
        initial={fromApi(data)}
        saving={update.isPending}
        onSave={(d) =>
          update.mutate(
            { id, data: toInput(d) },
            { onSuccess: () => router.push(GALLERY) },
          )
        }
      />
    </div>
  );
}
