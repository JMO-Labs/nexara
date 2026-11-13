"use client";
/**
 * @file lib/lists/fieldTypes/OptionsEditor.tsx
 * @brief Mini-table editor for {value,label} options.
 */
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { optionsOf, type FieldConfigEditorProps } from "./base";

const cell =
  "h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm";

/**
 * @brief ConfigEditor shared by select and multiselect.
 * @param props config and onChange
 * @return options form
 */
export function OptionsEditor({ config, onChange }: FieldConfigEditorProps) {
  const opts = optionsOf(config);
  const set = (options: typeof opts) => onChange({ ...config, options });
  const patch = (i: number, p: Partial<(typeof opts)[0]>) =>
    set(opts.map((o, j) => (j === i ? { ...o, ...p } : o)));
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold">Options</h4>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left">
            <th className="pb-1 font-medium">Value</th>
            <th className="pb-1 font-medium">Label</th>
            <th className="w-10">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {opts.map((o, i) => (
            <tr key={i}>
              <td className="pr-2 pb-1">
                <input
                  className={cell}
                  aria-label={`Value ${i + 1}`}
                  value={o.value}
                  onChange={(e) => patch(i, { value: e.target.value })}
                />
              </td>
              <td className="pr-2 pb-1">
                <input
                  className={cell}
                  aria-label={`Label ${i + 1}`}
                  value={o.label}
                  onChange={(e) => patch(i, { label: e.target.value })}
                />
              </td>
              <td className="pb-1">
                <IconButton
                  aria-label={`Delete option ${i + 1}`}
                  onClick={() => set(opts.filter((_, j) => j !== i))}
                >
                  <Trash2 className="size-4" />
                </IconButton>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Button
        type="button"
        variant="outline"
        onClick={() => set([...opts, { value: "", label: "" }])}
      >
        <Plus className="size-4" /> Add Option
      </Button>
    </div>
  );
}
