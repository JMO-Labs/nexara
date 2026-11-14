"use client";
/**
 * @file components/lists/TemplateGallery.tsx
 * @brief Grid of system and user templates with edit/clone actions.
 */
import { Copy, Pencil } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { IconButton } from "@/components/ui/IconButton";
import type { ListTemplate } from "@/lib/lists/templateModel";
import { TemplatePreview } from "./TemplatePreview";

interface Props {
  templates: ListTemplate[];
  onEdit: (t: ListTemplate) => void;
  onClone: (t: ListTemplate) => void;
}

/**
 * @brief Template gallery; preview revealed on hover/focus.
 * @param props templates and handlers
 * @return grid
 */
export function TemplateGallery({ templates, onEdit, onClone }: Props) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {templates.map((t) => (
        <li key={t.id} className="group">
          <Card className="flex flex-col gap-2 p-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">
                {t.name}
                {t.system && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    System
                  </span>
                )}
              </h3>
              <div className="flex gap-1">
                <IconButton
                  aria-label={`Clone ${t.name}`}
                  onClick={() => onClone(t)}
                >
                  <Copy className="size-4" />
                </IconButton>
                <IconButton
                  aria-label={`Edit ${t.name}`}
                  onClick={() => onEdit(t)}
                >
                  <Pencil className="size-4" />
                </IconButton>
              </div>
            </div>
            <div className="hidden max-h-48 overflow-auto group-focus-within:block group-hover:block">
              <TemplatePreview fields={t.fields} />
            </div>
          </Card>
        </li>
      ))}
    </ul>
  );
}
