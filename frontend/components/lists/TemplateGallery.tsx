"use client";
/**
 * @file components/lists/TemplateGallery.tsx
 * @brief Grid of system and user templates with edit/clone actions.
 */
import { Copy, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
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
 * @brief Template gallery; preview is a disclosure (works on touch/keyboard).
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
              <div className="flex min-w-0 items-center gap-2">
                <h3 className="truncate font-semibold">{t.name}</h3>
                {t.system && <Badge>System</Badge>}
              </div>
              <div className="flex shrink-0 gap-1">
                <IconButton
                  variant="glass"
                  size="sm"
                  aria-label={`Clone ${t.name}`}
                  onClick={() => onClone(t)}
                >
                  <Copy className="size-4" />
                </IconButton>
                <IconButton
                  variant="glass"
                  size="sm"
                  aria-label={`Edit ${t.name}`}
                  onClick={() => onEdit(t)}
                >
                  <Pencil className="size-4" />
                </IconButton>
              </div>
            </div>
            <details className="group">
              <summary className="cursor-pointer text-sm text-muted hover:text-ink">
                Preview fields
              </summary>
              <div className="mt-2 max-h-48 overflow-auto">
                <TemplatePreview fields={t.fields} />
              </div>
            </details>
          </Card>
        </li>
      ))}
    </ul>
  );
}
